#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from urllib.request import urlopen
from json import loads, dumps

from helpers import get_config, timestamp

class DarkSky:
    
    URL = 'https://api.darksky.net/forecast/{api_key}/{latitude},{longitude}'
    WANTED_DATA = {
                    'currently': ['summary', 'icon', 'precipProbability',
                                    'temperature', 'apparentTemperature',
                                    'humidity', 'windSpeed', 'windGust',
                                    'windBearing', 'cloudCover', 'uvIndex'],
                    'minutely': ['summary'],
                    'hourly': ['summary']}
    
    FAHRENHEIT_DATA = ['temperature', 'apparentTemperature']
    MPH_DATA = ['windSpeed', 'windGust']
    
    CARDINAL_DIRECTIONS = {
        0: ('N', 'north'),
        45: ('NE', 'northeast'),
        90: ('E', 'east'),
        135: ('SE', 'southeast'),
        180: ('S', 'south'),
        225: ('SW', 'southwest'),
        270: ('W', 'west'),
        315: ('NW', 'northwest')
        }
    
    WIND_STR = '{direction}erly, {speed}km/h (gusts of up to {gust}km/h).'
    TEMP_STR = '{temperature}°C (feels like {feels_like}°C).'
    
    def __init__(self, config):
        self.config = config
        self.API_KEY = config['API_KEYS']['DARKSKY']
        self.LATITUDE = config['DARKSKY']['LATITUDE']
        self.LONGITUDE = config['DARKSKY']['LONGITUDE']
    
    def to_celsius(self, f):
        return round((f-32) * 5 / 9, 2)
    
    def to_kmph(self, mph):
        return round(mph * 1.60934, 2)
    
    def wind_direction(self, bearing):
        diffs = {abs(bearing-i): i for i in self.CARDINAL_DIRECTIONS.keys()}
        closest_cardinal = diffs[min(diffs.keys())]
        return self.CARDINAL_DIRECTIONS[closest_cardinal]
    
    def filter_data(self, raw_data):
        data = {}
        for category in self.WANTED_DATA:
            data[category] = {}
            for datum in raw_data[category]:
                data[category][datum] = raw_data[category][datum]
                
    
    def get_weather_data(self):
        raw_data = self.fetch_data(self.LATITUDE, self.LONGITUDE)
        
        # Filter data, returning only the info we want.
        data = {}
        for category in self.WANTED_DATA:
            data[category] = {}
            for datum in self.WANTED_DATA[category]:
                data[category][datum] = raw_data[category][datum]
        
        # Convert certain data into the format we want.
        for d in self.FAHRENHEIT_DATA:
            data['currently'][d] = self.to_celsius(data['currently'][d])
        for d in self.MPH_DATA:
            data['currently'][d] = self.to_celsius(data['currently'][d])
        data['currently']['windDirection'] = self.wind_direction(data['currently']['windBearing'])
        
        # Generate a few user-friendly strings from certain data.
        data['text'] = {
            'wind': self.WIND_STR.format(
                            direction=data['currently']['windDirection'][1],
                            speed=data['currently']['windSpeed'],
                            gust=data['currently']['windGust']
                            ),
            'temperature': self.TEMP_STR.format(
                            temperature=data['currently']['temperature'],
                            feels_like=data['currently']['apparentTemperature']
                            ),
            'summary': data['currently']['summary'].replace('min.', 'minutes'),
            'minutely': data['minutely']['summary'].replace('min.', 'minutes'),
            'hourly': data['hourly']['summary'].replace('min.', 'minutes')
            }
        
        return data
        
    
    def fetch_data(self, latitude, longitude):
        url = self.URL.format(api_key=self.API_KEY, latitude=latitude,
                                longitude=longitude)
        json_data = urlopen(url).read().decode()
        data = loads(json_data)
        return data

def get_all_data():
    config = get_config()
    darksky = DarkSky(config)
    data = darksky.get_weather_data()
    timestamp(data)
    return data

if __name__ == '__main__':
    print(get_all_data())
