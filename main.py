import json
import os.path
import re
import datetime
import numpy as np
import requests
import matplotlib.pyplot as plt
from tqdm import tqdm


def get_data():
    file_location = "C:\\Program Files (x86)\\Steam\\logs"
    file_names = ["content_log.previous.txt", "content_log.txt"]
    p = re.compile('\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] AppID \d+ state changed : (\w| |,)+')
    last_times = dict()
    play_data = dict()
    for file_name in file_names:
        f = open(file_location + "\\" + file_name)
        for line in f:
            if p.match(line):
                date = datetime.datetime.strptime(line[1:20], '%Y-%m-%d %H:%M:%S')
                start_game = line.__contains__("App Running")
                game_id = int(line.split()[3])

                if game_id in last_times:
                    if game_id in play_data:
                        play_data[game_id].append({"start": last_times[game_id], "end": date})
                    else:
                        play_data[game_id] = [{"start": last_times[game_id], "end": date}]
                    del last_times[game_id]
                elif start_game:
                    last_times[game_id] = date
    return play_data


def plot_stats(data, game_names, days):
    fig = plt.figure()
    ax = fig.add_axes([0.1, 0.15, 0.8, 0.75])

    plt.plot(list(map(list, zip(*data))))

    # ax.set_xticklabels([day.strftime("%Y-%m-%d") for day in days])
    # ax.set_xticks(range(len(days)))
    plt.xticks(range(len(days)), [day.strftime("%Y-%m-%d") for day in days], rotation=30, ha="right")

    plt.legend(game_names.values())
    plt.show()
    return


def get_day_span(game_stats):
    min_date = min([min([time['start'] for time in item]) for item in game_stats.values()])
    max_date = max([max([time['end'] for time in item]) for item in game_stats.values()])
    return min_date, max_date


def gen_dates(min_date, max_date):
    new_min_date = min_date.replace(hour=0, minute=0, second=0) + datetime.timedelta(days=0)
    new_max_date = max_date.replace(hour=0, minute=0, second=0) + datetime.timedelta(days=1)
    return [new_min_date + datetime.timedelta(days=x) for x in range((new_max_date - new_min_date).days)]


def gen_time_stats(game_stats):
    game_ids = list(game_stats.keys())
    min_date, max_date = get_day_span(game_stats)
    day_count = max_date.toordinal() - min_date.toordinal() + 1
    game_count = len(game_stats)
    data = np.zeros((game_count, day_count))

    for game_id in game_stats:
        for time in game_stats[game_id]:
            date_index = time['start'].toordinal() - min_date.toordinal()
            game_index = game_ids.index(game_id)
            game_time = (time['end'] - time['start']).total_seconds() / 3600
            data[game_index][date_index] += game_time

    return data, min_date, max_date


def get_game_names(game_ids):
    api_url = 'https://store.steampowered.com/api/appdetails'
    with open("name_cache", "r") as readfile:
        names = json.loads(readfile.read())
    for game_id in tqdm(game_ids):
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


def main():
    if not os.path.isfile("name_cache"):
        with open("name_cache", "w") as writefile:
            writefile.write("{}")

    play_data = get_data()
    game_ids = list(play_data.keys())
    game_names = get_game_names(game_ids)

    stat_matrix, min_date, max_date = gen_time_stats(play_data)
    dates = gen_dates(min_date, max_date)
    plot_stats(stat_matrix, game_names, dates)


if __name__ == '__main__':
    main()
