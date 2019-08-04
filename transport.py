#!/usr/bin/env python3

# TODO:  Why even have nginx serve the main page?  Just have static html file?

from time import localtime, strftime
from urllib.request import urlopen
from os.path import join, expanduser
from json import loads, dumps
from configparser import ConfigParser

class RTPIError(Exception): pass

class RTPIData:

    MODES = {'BUS', 'LUAS', 'BIKE'}

    RTPI_URL =  ('https://data.smartdublin.ie/cgi-bin/rtpi/'
                'realtimebusinformation?stopid={}')
    
    DB_URL =    ('https://api.jcdecaux.com/vls/v1/stations/{}'
                '?contract=Dublin&apiKey={}')

    RTPI_WANTED_DATA = {'duetime', 'destination', 'route', 'additionalinformation',
            'direction'}

    def __init__(self, config=None, conf_file=None):
        
        self.config = config or self.load_config()
        self.conf_file = conf_file or expanduser('~/.config/dublin_data.ini')

    def load_config(self, conf_file=None):

        self.config = ConfigParser()
        self.config.optionxform = lambda option: option
        self.config.read(self.conf_file)

        self.RESULT_COUNT = self.config.getint('CONFIG_VALUES', 'RESULT_COUNT')
        self.DB_API_KEY = self.config['CONFIG_VALUES']['DB_API_KEY']

        self.LUAS_STOPS = self.config['LUAS_STOPS']
        self.BUS_STOPS = self.config['BUS_STOPS']
        self.BIKE_STOPS = self.config['BIKE_STOPS']

    def get_all_data(self):

        return self.get_data(*self.MODES)

    def get_data(self, *modes):

        results = {}
        if 'LUAS' in modes:
            results['LUAS'] = self.get_rtpi_data('LUAS')
        if 'BUS' in modes:
            results['BUS'] = self.get_rtpi_data('BUS')
        if 'BIKE' in modes:
            results['BIKE'] = self.get_bike_data()
        results['timestamp'] = localtime()
        results['timestamp_str'] = strftime('%H:%M:%S on %A %d %B %Y')
        return results

    def get_rtpi_data(self, bus_or_luas, de_dup=True):

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

    def get_bike_data(self):

        data = {}
        for stop in self.BIKE_STOPS:
            stop_id = self.BIKE_STOPS[stop]
            data[stop] = self.fetch_bike_data(stop_id)
        return data

    # Functions to fetch data from APIs

    def fetch_rtpi_data(self, stop_id):

        url = self.RTPI_URL.format(stop_id)
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

    def fetch_bike_data(self, stop_id):

        url = self.DB_URL.format(stop_id, self.DB_API_KEY)
        json_data = urlopen(url).read().decode()
        data = loads(json_data)
        return data['status'], data['available_bikes'], data['bike_stands']

class BikeData:

# Callable for WSGI so that script can run as webserver

def application(environ, start_response):
    dtd = DublinTransportData()
    data = dtd.get_all_data()
    start_response('200 OK', [('Content-Type','application/json'),
        ('Access-Control-Allow-Origin', '*')])
    return [bytes(dumps(data), 'utf-8')]

if __name__ == '__main__':
    dtd = DublinTransportData()
    print(dtd.get_all_data())
