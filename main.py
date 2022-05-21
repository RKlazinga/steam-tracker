import math
import json
import os.path
import pickle
import re
import datetime
from collections import defaultdict
from datetime import datetime as dt
from enum import Enum

import numpy as np
import requests
import matplotlib.pyplot as plt


class PlotType(Enum):
    LINE = 1
    STACKED_LINE = 2


def get_data():
    file_location = "C:\\Program Files (x86)\\Steam\\logs"
    file_names = ["content_log.previous.txt", "content_log.txt"]
    p = re.compile('\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}] AppID \d+ state changed : (\w| |,)+')
    last_times = dict()
    play_data = defaultdict(list)
    for file_name in file_names:
        f = open(file_location + "\\" + file_name)
        for line in f:
            if p.match(line):
                date = datetime.datetime.strptime(line[1:20], '%Y-%m-%d %H:%M:%S')
                start_game = line.__contains__("App Running")
                game_id = int(line.split()[3])

                if game_id in last_times:
                    play_data[game_id].append((int(dt.timestamp(last_times[game_id])),
                                               int(dt.timestamp(date))))
                    del last_times[game_id]
                elif start_game:
                    last_times[game_id] = date
    return play_data


def get_data_step_size(max_val):
    if max_val < 60:
        return 5
    if max_val < 120:
        return 15
    if max_val < 300:
        return 30
    return 60


def plot_stats(data, game_names, days, plot_type=PlotType.LINE):
    fig = plt.figure()
    fig.add_axes([0.1, 0.15, 0.8, 0.75])

    if plot_type == PlotType.LINE:
        plt.plot([*zip(*data)])
    if plot_type == PlotType.STACKED_LINE:
        plt.stackplot(range(len(days)), data)

    y_step_size = get_data_step_size(np.amax(data))
    plt.yticks(np.arange(0, math.ceil(np.amax(data) / y_step_size + 1) * y_step_size, y_step_size))
    plt.xticks(range(len(days)), [day.strftime("%Y-%m-%d") for day in days], rotation=30, ha="right")

    plt.grid()
    plt.legend(game_names.values())
    plt.show()
    return


def get_day_span(game_stats):
    min_date = min([time[0] for item in game_stats.values() for time in item])
    max_date = max([time[1] for item in game_stats.values() for time in item])
    return dt.fromtimestamp(min_date), dt.fromtimestamp(max_date)


def gen_dates(min_date, max_date):
    new_min_date = min_date.replace(hour=0, minute=0, second=0) + datetime.timedelta(days=0)
    new_max_date = max_date.replace(hour=0, minute=0, second=0) + datetime.timedelta(days=1)
    return [new_min_date + datetime.timedelta(days=x) for x in range((new_max_date - new_min_date).days)]


def day_diff(date1, date2):
    return abs(date1.toordinal() - date2.toordinal())


def gen_time_stats(game_stats):
    game_ids = list(game_stats.keys())
    min_date, max_date = get_day_span(game_stats)
    day_count = day_diff(max_date, min_date) + 1
    game_count = len(game_stats)
    data = np.zeros((game_count, day_count))

    for game_id in game_stats:
        for time in game_stats[game_id]:
            date_index = day_diff(dt.fromtimestamp(time[0]), min_date)
            game_index = game_ids.index(game_id)
            game_time = (time[1] - time[0]) / 60
            data[game_index][date_index] += game_time

    return data, min_date, max_date


def get_game_names(game_ids):
    api_url = 'https://store.steampowered.com/api/appdetails'
    with open("name_cache", "r") as readfile:
        names = json.loads(readfile.read())
    for game_id in game_ids:
        if str(game_id) not in names:
            params = dict(
                appids=game_id
            )
            resp = requests.get(url=api_url, params=params)
            data = resp.json()
            names[str(game_id)] = data[str(game_id)]["data"]["name"]
    with open("name_cache", "w") as writefile:
        writefile.write(json.dumps(names))
    return names


def save_data(play_data):
    binary_data = pickle.dumps(play_data)
    with open("play_data_cache", "wb") as writefile:
        writefile.write(binary_data)


def load_data():
    with open("play_data_cache", "rb") as readfile:
        binary_data = readfile.read()
        play_data = pickle.loads(binary_data)
        return play_data


def merge_data(data1, data2):
    for game_id in data2:
        data1[game_id] = list(set(data1[game_id] + data2[game_id]))
    return data1


def main():
    if not os.path.isfile("name_cache"):
        with open("name_cache", "w") as writefile:
            writefile.write("{}")

    play_data = get_data()
    cached_data = load_data()
    play_data = merge_data(cached_data, play_data)
    save_data(play_data)

    game_ids = list(play_data.keys())
    game_names = get_game_names(game_ids)

    stat_matrix, min_date, max_date = gen_time_stats(play_data)
    dates = gen_dates(min_date, max_date)
    plot_stats(stat_matrix, game_names, dates)


if __name__ == '__main__':
    main()
