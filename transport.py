#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# TODO:  Why even have nginx serve the main page?  Just have static html file?

from urllib.request import urlopen
from json import loads, dumps

from helpers import get_config, timestamp

class RTPIError(Exception): pass

class RTPI:

    SERVICES = {'BUS', 'LUAS'}

    URL =  ('https://data.smartdublin.ie/cgi-bin/rtpi/'
                'realtimebusinformation?stopid={stop_id}')

    RTPI_WANTED_DATA = {'duetime', 'destination', 'route', 'additionalinformation',
            'direction'}

    def __init__(self, config):
        
        self.config = config
        self.RESULT_COUNT = self.config.getint('CONFIG_VALUES', 'RESULT_COUNT')
        self.LUAS_STOPS = self.config['LUAS_STOPS']
        self.BUS_STOPS = self.config['BUS_STOPS']

    def get_all_data(self):
        
        data = {}
        for s in self.SERVICES:
            data[s] = self.get_rtpi_data(s)
        return data

    def get_rtpi_data(self, bus_or_luas, de_dup=True):
        """Fetch API data according to config and return in an easily usable format."""
        if bus_or_luas == 'BUS':
            stops = self.BUS_STOPS
        elif bus_or_luas == 'LUAS':
            stops = self.LUAS_STOPS
        else:
            raise ValueError('Argument must be "BUS" or "LUAS"')

        data = {'Inbound': [], 'Outbound': []}
        for stop in stops:
            stop_id = stops[stop]
            results = self.fetch_rtpi_data(stop_id)
            if results is not None:
                for r in results:
                    dest = r['direction']
                    relevant_data = {k:r.get(k) for k in r if k in self.RTPI_WANTED_DATA}
                    relevant_data['stop'] = stop
                    add_result = True
                    if de_dup:
                        # Compare new result against each already recorded result (going the same direction).
                        # If there is an existing result and the destination and route are the same BUT the
                        # departing stops are DIFFERENT, then do not add the result.  This will allow us to
                        # list multiple consecutive services going from the same stop but will remove any
                        # such services departing from lower priority stops.  This assumes that a given
                        # route will always serve all the same stops; if it is possible for a service to
                        # sometimes serve stops A and B but other times only serve stop B, this may result
                        # in the complete exclusion of certain buses that only serve stop B.
                        for _r in data[dest]:
                            if (_r['destination'] == r['destination']) and (_r['route'] == r['route']) and (_r['stop'] != stop):
                                add_result = False
                    if add_result:
                        data[dest].append(relevant_data)

        for dest in data:
            data[dest] = sorted(data[dest],
                    key=lambda r: 0 if r['duetime'] == 'Due' else int(r['duetime'])
                    )[:self.RESULT_COUNT]
        
        return data

    def fetch_rtpi_data(self, stop_id):
        """Fetch relevant data from API and return it."""
        url = self.URL.format(stop_id=stop_id)
        json_data = urlopen(url).read().decode()
        data = loads(json_data)
        if data['errorcode'] == '0':
            results = data['results']
            #return [(r['route'], r['destination'], r['duetime']) for r in results]
            return results
        elif data['errorcode'] == '1':
            return None
        else:
            raise RTPIError(data['errorcode'], data['errormessage'])


class DublinBikes:
    
    URL =    ('https://api.jcdecaux.com/vls/v1/stations/{stop_id}'
                '?contract=Dublin&apiKey={api_key}')
    
    def __init__(self, config):
        
        self.config = config
        self.API_KEY = self.config['API_KEYS']['DUBLINBIKES']
        self.BIKE_STOPS = self.config['BIKE_STOPS']
    
    def get_bike_data(self, with_label=True):
        """Fetch API data according to config and return in an easily usable format."""
        data = {}
        for stop in self.BIKE_STOPS:
            stop_id = self.BIKE_STOPS[stop]
            data[stop] = self.fetch_bike_data(stop_id)
        if with_label:
            return {'BIKE': data}
        else:
            return data

    def fetch_bike_data(self, stop_id):
        """Fetch relevant data from API and return it.""" 
        url = self.URL.format(stop_id=stop_id, api_key=self.API_KEY)
        json_data = urlopen(url).read().decode()
        data = loads(json_data)
        return data['status'], data['available_bikes'], data['bike_stands']

def get_all_data():
    conf = get_config()
    rtpi = RTPI(conf)
    db = DublinBikes(conf)
    data = rtpi.get_all_data()
    data.update(db.get_bike_data())
    timestamp(data)
    return data

if __name__ == '__main__':
    print(get_all_data())
