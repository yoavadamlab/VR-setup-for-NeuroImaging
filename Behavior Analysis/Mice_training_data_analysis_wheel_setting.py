
# coding: utf-8

# ## Metadata preparation

# In[227]:


# 1.read config data - generate bulks of date & cage: data[cage][name][stage][weight]
# 2.read weight base line
# 3. write weight to weight table
# 4. execute plots per cage per state & update table for daily
# 5. read data from table
# 6. generate daily txt update per stage
# 7. send it by email

from os.path import isfile, join
from os import listdir
import warnings
import csv
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn
from email.mime.text import MIMEText
import smtplib
import datetime as dt
from fpdf import FPDF
from os.path import basename
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate


MICE_TRAINING_DIR = "enter here your Mice Training dir path"

BINS_NUMBER = 140  # i.e each bin ~ 1 cm
WINDOW_SIZE = 3  # how many bins to average
START_VIRNMEN_POSTION = -30
START_GIVE_REWARD = 107

# need to be configured
MAX_LAP_LENGTH = 1700
MIN_LAP_LENGTH = 1400

seaborn.set(style='ticks')
# run after each cage


def read_training_meta_data():
    # read metadata_table from virmen, extract not analyzed rows and mark them as analyzed
    file_path = MICE_TRAINING_DIR + \
        "\helper_data_tabels\\training_metadata_from_virmen.csv"
    # This will hold our information for later (since we can't both read and write simultaneously)
    new_file = []
    header = ''
    mice_list = []
    with open(file_path, 'rt') as f:
        reader = csv.reader(f, delimiter=',')
        for i, line in enumerate(reader):
            # append all lines to the new file
            # but change the anlyzed value to 1
            if i == 0:
                header = line
                new_file.append(line)
                continue
            if len(line) == 0:
                continue
            if line[5] == '0':  # not analyzed data
                mice_list.append(line[0:5])
                new_line = line[0:5] + [1]
                new_file.append(new_line)
            else:
                new_file.append(line)
    with open(file_path, 'w', newline='') as f:
        writer = csv.writer(f, delimiter=',')
        for line in new_file:    # Write all of our new information back into the new file.
            writer.writerow(line)
    header = ['date', 'cage', 'name', 'stage', 'weight', 'analyzed']
    config_data = pd.DataFrame(mice_list, columns=header[0:5])
    # data, cage, name. stage, weight; just of not analyzed data
    config_data['date'] = pd.to_datetime(config_data['date'], dayfirst=True)
    config_data['date'] = config_data['date'].dt.date
    return config_data


def read_baseline(mouse_name, cage):
    """
    read baseline weight.
    assuming that the first line is the baseline weight
    """
    path = '\weight_tracking\\'
    cage_weight_table = MICE_TRAINING_DIR + path + cage + '.csv'
    df = pd.read_csv(cage_weight_table)
    baseline_weight = df.iloc[0][mouse_name]
    return baseline_weight


def update_weight(cage_name, mouse_name, training_date_date_format, weight):
    day = str(training_date_date_format.day)
    month = str(training_date_date_format.month)
    year = str(training_date_date_format.year)[2:]
    training_date = day + '.' + month + '.' + year
    path = '\weight_tracking\\'
    cage_weight_table = MICE_TRAINING_DIR + path + cage_name + '.csv'
    # This will hold our information for later (since we can't both read and write simultaneously)
    new_file = []
    header = ''
    mice_list = []
    date_exist = False
    with open(cage_weight_table, 'rt') as f:
        reader = csv.reader(f, delimiter=',')
        for i, line in enumerate(reader):
            # append all lines to the new file
            # but change the anlyzed value to 1
            if i == 0:
                header = line
                new_file.append(line)
                continue
            if len(line) == 0:
                continue
            if line[0] == training_date:
                date_exist = True
                new_line = []
                for i, col in enumerate(line):
                    if header[i] == mouse_name:
                        new_line.append(weight)
                    else:
                        new_line.append(line[i])
                new_file.append(new_line)
            else:
                new_file.append(line)
        if not date_exist:
            new_line = []
            new_line.append(training_date)
            for i, haed in enumerate(header):
                if i == 0:
                    continue
                if header[i] == mouse_name:
                    new_line.append(weight)
                else:
                    new_line.append('')
            new_file.append(new_line)
    with open(cage_weight_table, 'w', newline='') as f:
        writer = csv.writer(f, delimiter=',')
        for line in new_file:    # Write all of our new information back into the new file.
            writer.writerow(line)
    return


# # General preparation for analytics
# ## read virmen data

# In[273]:
warnings.simplefilter(action='ignore')
# maximum data to show
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)


def read_virmen_data(mice_cages):
    """
    read tdms files from neurotar tracking tdms files to a pandas dataframe.
    The function assuming that the data is in "Tracking" directory in the shared
    Adam-lab directory and in the format of cage_mousename dir name.
    : param: mice_cages: list of cages to read from the Tracking directory
    e.g  mice_cages = ["GC4"]
    : return: list of tupels. the first entry is a 3-entry tuple of
    cage name, mouse name and training date and the second entry is the df itself.

    """
    # readind the relevant pathes
    tracking_path = MICE_TRAINING_DIR + "/training_data"
    csv_paths = []
    for subdir, dirs, files in os.walk(tracking_path):
        # read pathes of the mouses cages in mice_cages list
        if any(cage in subdir for cage in mice_cages):
            for filename in files:
                filepath = subdir + os.sep + filename

                if filepath.endswith(".csv"):
                    csv_paths.append(filepath)
    # saved the data from the cages
    dfs = []  # will contain the tdms in df format
    for csv_path in csv_paths:
        # read the tdms from neurotar to df
        df = pd.read_csv(csv_path)
        # parse cage name, nouse name and training date
        cage_mouse_date = csv_path.split(
            "Mice_Training/training_data\\")[1].split("\\")
        cage = cage_mouse_date[0]
        mouse = cage_mouse_date[1]
        date = os.path.splitext(cage_mouse_date[2])[0]
        # each df saved with tuple of cage name, mouse name and date
        dfs.append(((cage, mouse, date), df))
    return dfs


def data_preparation(dfs):
    """
    return the dfs with the follwing columns only:
    'pp_phi', 'pp_x'  , 'pp_y' , 'pp_speed' , 'pp_zone' , 'lick', 'reward'
    where pp stand for post prossecing section fron neurotar tdms file
    and lick and reward extracted from the input column and separated to two columns.
    """
    fixed_dfs = []
    for data in dfs:
        df = data[1]  # the df
        df['cage'] = data[0][0]
        df['name'] = data[0][1]
        df['date'] = pd.to_datetime(data[0][2], dayfirst=True)
        df['day'] = pd.DatetimeIndex(df['date']).day
        df['month'] = pd.DatetimeIndex(df['date']).month
        df['year'] = pd.DatetimeIndex(df['date']).year
        df['day_and_month'] = df['day'].astype(
            str) + '-' + df['month'].astype(str)
        df['date'] = df['date'].dt.date
        fixed_dfs.append(df)
    df = pd.concat(fixed_dfs)
    # rearange columns order
    cols = df.columns.tolist()
    cols = cols[-8:] + cols[:-8]
    df = df[cols]
    return df


def add_columns(data):
    """
    The follwing columns are added:
    prev_phi - the phi from previous frame
    lap length - bad column. per each lap indicate the sum of movment/ big variation between laps (~20 cm diffrences)
    lap_duration - lap duration in miliseconds. the values in the columns will be identical at all the rows of a specific lap
    lick_indicator - will be 1 at the first frame of licking period, otherwise 0
    reward_indicator - will be 1 at the first frame of reward period, otherwise 0
    In addition - the lap total movement isn't acuurate - bettwer to work with positin - very accurate!
    ## update 24.01.22 - 
    We change the training setting to a spinnig wheel rather than Neurotar system.
    This implies a few changes in the saving data format from VirMen.
    The most important one - we don't use any more the air flag to indicate whether the mous us runnig or resting
    To avoid changing a lot of the training analysis code we add an "air" column to the data.
    it will be set to 1 when the "resting" column is 0, and vice versa.
    This will keep the code in the same architecture and won't change anything else.
    """
    df = data.copy()
    df["air"] = (df["resting"] * (-1)) + 1 # 0 --> 1, 1 -->0
    #df['prev_phi'] = df.groupby(['cage', 'name', 'day', 'month', 'year'])['phi'].shift()
    #df.fillna(method='bfill', inplace=True)
    df.loc[df.speed <= 10, 'movement'] = 0  # zero movement
    # cumsum of the movement column for getting the milmetric distance that the mouse run
    df['position_mm'] = df.groupby(
        ['cage', 'name', 'day', 'month', 'year', 'lap_counter', 'current_World'])['movement'].cumsum()
    # lap length
    df['lap_length'] = df.groupby(['cage', 'name', 'day', 'month', 'year', 'lap_counter',
                                  'current_World']).movement.transform('sum')  # the total distance per lap
    # add lick_indicator
    df['prev_lick'] = df.groupby(['cage', 'name', 'day', 'month', 'year'])[
        'lick'].shift()
    df.fillna(method='bfill', inplace=True)
    condition = (df['prev_lick'] != df['lick']) & (df['lick'].astype(int) == 1)
    df['lick_indicator'] = np.where(condition, 1, 0)
    # add reward_indicator
    df['prev_reward'] = df.groupby(['cage', 'name', 'day', 'month', 'year'])[
        'reward'].shift()
    df.fillna(method='bfill', inplace=True)
    condition = (df['prev_reward'] != df['reward']) & (
        df['reward'].astype(int) == 1)
    df['reward_indicator'] = np.where(condition, 1, 0)
    df['prev_world'] = df.groupby(['cage', 'name', 'day', 'month', 'year'])[
        'current_World'].shift()
    df.fillna(method='bfill', inplace=True)
    condition = (df['prev_world'] != df['current_World'])
    df['change_world'] = np.where(condition, 1, 0)
    df['world_indicator'] = df.groupby(['cage', 'name', 'day', 'month', 'year'])[
        'change_world'].cumsum()
    return df


def add_lap_duration(data):
    # add lap duration
    # calc separate time period during the lap and than sum them
    # add air_state - air stets during the lap. three posiablities:
    # 1. the air was working or wasn't working duting all the lap - only 0 state
    # 2. the lap started with air and finished withot air - two states
    # 3. the lap started with air, the valve close and than reopen after two minutes and the mouse stay in the same lap - 3 states
    df = data.copy()
    df['prev_air'] = df.groupby(['cage', 'name', 'date', 'lap_counter'])[
        'air'].shift()
    df.fillna(method='bfill', inplace=True)
    df['air_indicator'] = np.where(df['prev_air'] != df['air'], 1, 0)
    df['air_state'] = df.groupby(['cage', 'name', 'date', 'lap_counter'])[
        'air_indicator'].cumsum()
    df = df[df['air'] == 1]
    group = df.groupby(['cage', 'name', 'date', 'lap_counter', 'air_state'])
    df['lap_duration_per_air_state'] = group['timeElapsed'].transform(
        max) - group['timeElapsed'].transform(min)
    df = df[['cage', 'name', 'date', 'lap_counter', 'air_state',
             'lap_duration_per_air_state']].drop_duplicates()
    df['lap_duration'] = df.groupby(['cage', 'name', 'date', 'lap_counter'])[
        'lap_duration_per_air_state'].transform('sum')
    df = df[['cage', 'name', 'date', 'lap_counter',
             'lap_duration']].drop_duplicates()
    # after calculate per each lap the duration - join it to the main table
    data = data.merge(df, on=['cage', 'name', 'date',
                      'lap_counter'], how='left')
    return data


def build_data_table(mice_cages):
    dfs = read_virmen_data(mice_cages)
    data = data_preparation(dfs)
    data = add_columns(data)
#     data = add_lap_duration(data)
    return data


# ## weight plot

# In[148]:


def weight_plot(cage_name, mouse_name, training_date_date_format, baseline_weight):
    day = str(training_date_date_format.day)
    month = str(training_date_date_format.month)
    year = str(training_date_date_format.year)[2:]
    training_date = day + '.' + month + '.' + year
    eighty_percent = baseline_weight * 0.8
    path = '\weight_tracking\\'
    cage_weight_table = MICE_TRAINING_DIR + path + cage_name + '.csv'
    df = pd.read_csv(cage_weight_table)
    fig, axis = plt.subplots(1, 1, figsize=(20, 9))
    df.set_index('date', inplace=True)
    df[mouse_name].plot(ax=axis, label='_nolegend_')

    axis.axhline(eighty_percent, c='red', linewidth=2.5,
                 ls='--', label="80% from baseline")
    axis.set_xlabel("Date")
    axis.set_ylabel("Weight [g]")
    axis.legend(fontsize=15)
    axis.set_title(cage_name + "/" + mouse_name +
                   " - Weight during water restriction", fontsize=20)
    save_dir = MICE_TRAINING_DIR + '\\analyzed_data\\plots\\' + \
        cage_name + '\\' + training_date + '\\'
    save_file = mouse_name + "_weight_plot" + '.png'

    fig.tight_layout()

    if not os.path.isdir(save_dir):
        os.makedirs(save_dir)
    fig.savefig(save_dir + save_file, bbox_inches='tight')
    return


# ## calc running and resting time

# In[249]:


def running_and_resting_time(data):
    """
    assuming that "data" is one mouse df of one training date
    """
    df = data.copy()
    df['prev_timeElapsed'] = df['timeElapsed'].shift()
    df.fillna(method='bfill', inplace=True)
    df['time_between_frames'] = df['timeElapsed'] - df['prev_timeElapsed']
    df = df[['cage', 'name', 'date', 'time_between_frames', 'air']]
    df['time_per_air_state'] = df.groupby(
        ['air']).time_between_frames.transform('sum')
    df['time_per_air_state (minutes)'] = (
        (df['time_per_air_state'] / 60) * 1e1).astype(float) / 1e1
    df = df[['cage', 'name', 'date', 'air',
             'time_per_air_state (minutes)']].drop_duplicates()
    air_on_table = df[df['air'] == 1]
    air_on = air_on_table.iloc[0]['time_per_air_state (minutes)']
    air_off_table = df[df['air'] == 0]
    air_off = air_off_table.iloc[0]['time_per_air_state (minutes)']
    total_time = air_on + air_off
    # trunc
    total_time = (int(total_time * 1e2) / 1e2)
    air_on = (int(air_on * 1e2) / 1e2)
    air_off = (int(air_off * 1e2) / 1e2)
    return air_on, air_off, total_time


# # get positions of reward zone per world

# In[281]:


def get_positions_of_reward_zone(data):
    # assuming the virmen reward zone are:
    START_RWD_VIRMEN_WORLD_1 = 107
    END_RWD_VIRMEN_WORLD_1 = 128
    START_RWD_VIRMEN_WORLD_2 = 107
    END_RWD_VIRMEN_WORLD_2 = 128
    START_RWD_VIRMEN_WORLD_3 = 105
    END_RWD_VIRMEN_WORLD_3 = 128
    df = data.copy()
    df = df[['date', 'lap_counter', 'position', 'position_mm',
             'current_World', 'reward']].drop_duplicates()
    world_data = df.groupby('current_World')
    dict_of_coordinates = {}
    for name_of_world, world_table in world_data:
        if name_of_world == 1:
            START_RWD_VIRMEN = START_RWD_VIRMEN_WORLD_1
            END_RWD_VIRMEN = END_RWD_VIRMEN_WORLD_1
        if name_of_world == 2:
            START_RWD_VIRMEN = START_RWD_VIRMEN_WORLD_2
            END_RWD_VIRMEN = END_RWD_VIRMEN_WORLD_2
        if name_of_world == 3:
            START_RWD_VIRMEN = START_RWD_VIRMEN_WORLD_3
            END_RWD_VIRMEN = END_RWD_VIRMEN_WORLD_3
        # taking start rwd_zone by the rwaed position
        dff = world_table.copy()
        dff = dff[dff["reward"] == 1]
        dff["start_rwd_mm"] = dff.groupby(
            ['date', 'lap_counter']).position_mm.transform('min')
        dff = dff[['date', 'lap_counter', 'start_rwd_mm']].drop_duplicates()
        start_rwd = dff["start_rwd_mm"].median()

        world_table = world_table[(world_table['position'] >= START_RWD_VIRMEN) & (
            world_table['position'] <= END_RWD_VIRMEN)]
        world_table['start_rwd_mm'] = world_table.groupby(
            ['lap_counter']).position_mm.transform('min')
        world_table['end_rwd_mm'] = world_table.groupby(
            ['lap_counter']).position_mm.transform('max')
        world_table = world_table[[
            'lap_counter', 'start_rwd_mm', 'end_rwd_mm']].drop_duplicates()
        # start_rwd = world_table['start_rwd_mm'].mean()
        end_rwd = world_table['end_rwd_mm'].mean()
        dict_of_coordinates[name_of_world] = (start_rwd, end_rwd)
    return dict_of_coordinates


# In[240]:


def calc_analytics(data, cage_name, mouse_name, training_date, training_date_str, stage, weight, baseline_weight):
    weight_plot(cage_name, mouse_name, training_date, baseline_weight)
    if stage == "B":
        results = stage_B_analytics(data, cage_name, mouse_name, training_date)
        generate_daily_update_stage_B(
            results, cage_name, mouse_name, weight, baseline_weight, training_date)
    if stage == "C" or stage == "D" or stage == "E":
        results = stage_CDE_analytics(
            data, cage_name, mouse_name, training_date, training_date_str)
        generate_daily_update_stage_CDE(
            results, cage_name, mouse_name, weight, baseline_weight, training_date, stage, training_date_str)
    if stage == "F":
        results = stage_F_analytics(
            data, cage_name, mouse_name, training_date, training_date_str)
        generate_daily_update_stage_F(
            results, cage_name, mouse_name, weight, baseline_weight, training_date, stage, training_date_str)
    return


# # stage F analytics
#

# In[394]:

def stage_F_analytics(data, cage_name, mouse_name, training_date, training_date_str):
    df = data.copy()
    df = df[df["name"] == mouse_name]
    lap_duration_dict = lap_duration_stage_F(
        df, training_date, cage_name, mouse_name, training_date_str)
    speed_plot_two_worlds_history(
        df, cage_name, mouse_name, training_date, training_date_str)
    lick_rate_plot_two_worlds_history(
        df, cage_name, mouse_name, training_date, training_date_str)
    df = df[df["date"] == training_date]
    speed_plot_two_world_last_day(
        df, cage_name, mouse_name, training_date, training_date_str)
    lick_rate_plot_two_worlds_last_day(
        df, cage_name, mouse_name, training_date, training_date_str)
    world_air_time_dict = running_and_resting_time_multiple_worlds(df)
    world_rewards_num_dict = num_of_rewards_per_world(
        df)  # total will be the sum
    return world_air_time_dict, world_rewards_num_dict, lap_duration_dict


# ## speed plot - stage F

# In[393]:

def lick_rate_plot_two_worlds_history(data, cage_name, mouse_name, training_date, training_date_str):
    df = data.copy()
    df = df[df['air'] == 1]
    df = df[df['stage'] >= 3]
    df = df[df['current_World'] != 5]
    df = df[(df['lap_length'] >= MIN_LAP_LENGTH) & (df['lap_length'] <= MAX_LAP_LENGTH)]
    df["world"] = df.groupby(['lap_counter']).current_World.transform('min')
    #  start and end reward zone
    dict_of_positions = get_positions_of_reward_zone(df)

    # generate bin column
    bins_number = BINS_NUMBER  # i.e each bin ~ 1 cm
    window_size = WINDOW_SIZE  # how many bins to average
    labels = np.arange(bins_number)
    df['binned_mm_position'], bins = pd.cut(
        df['position_mm'], bins=bins_number, labels=labels, include_lowest=True, retbins=True)  # binning
    # generate lick per bin and time per bin, both per lap (since we measure time) ,columns
    # contains only good laps so the calculations is good
    group = df.groupby(['date', 'world', 'binned_mm_position'])
    df['right_end_of_bin'] = group['position_mm'].transform(
        'max')  # taking the mm value of the bin
    df['mean_speed_per_bin'] = group['speed'].transform('mean')
    group = df.groupby(['date', 'world', 'lap_counter', 'binned_mm_position'])
    df['licks_per_bin_in_lap'] = group['lick_indicator'].transform('sum')
    df['time_in_in_bin_in_lap'] = (group['timeElapsed'].transform(
        max) - group['timeElapsed'].transform(min)) + 0.035
    # unique row per bin per lap per mouse per date
    df = df[['world', 'date', 'lap_counter', 'binned_mm_position', 'right_end_of_bin',
             'licks_per_bin_in_lap', 'time_in_in_bin_in_lap']].drop_duplicates()
    # construct data that sum over all laps - just bins is important from now
    group = df.groupby(['world', 'date', 'binned_mm_position'])
    df['licks_per_bin'] = group['licks_per_bin_in_lap'].transform('sum')
    df['time_in_in_bin'] = group['time_in_in_bin_in_lap'].transform('sum')
    df = df[['date', 'binned_mm_position', 'right_end_of_bin',
             'licks_per_bin', 'time_in_in_bin']].drop_duplicates()
    df['lick_rate'] = df['licks_per_bin'] / df['time_in_in_bin']

    # sort
    df = df.sort_values(['world', 'date', 'binned_mm_position'],
                        ascending=[True, False, True])
    #  smoothing the curve
    df['smooth_lick_rate'] = df.groupby(['world', 'date'])['lick_rate'].transform(
        lambda s: s.rolling(window_size, min_periods=1, center=False).mean())
    df['position_cm'] = df['right_end_of_bin'] / 10
    df = df[df['binned_mm_position'] != 0]  # delete non continues bin
    # plotting

    fig, axis = plt.subplots(2, 2, figsize=(20, 9))
    dates = df['date'].drop_duplicates()
    total_dates = len(dates)
    alpha_vals = np.linspace(0.1, 0.6, total_dates)
    j = 0  # for alpha vals
    df.set_index('position_cm', inplace=True)
    date_groups = df.groupby('date')
    for date_name, day_table in date_groups:
        world_group = day_table.groupby('world')
        for world_idx, world_tuple in enumerate(world_group):
            world_name, world_table = world_tuple
            START_REWARD, END_REWARD = dict_of_positions[world_name]
            if date_name == training_date:
                world_table['smooth_lick_rate'].plot(
                    ax=axis[0][world_idx], label='_nolegend_')
                axis[0][world_idx].axvline(
                    x=START_REWARD / 10, c='red', linewidth=2.5, ls='--', label=("reward_zone_" + str(world_name)))
                axis[0][world_idx].axvline(
                    x=END_REWARD / 10, c='red', linewidth=2.5, ls='--')
                axis[0][world_idx].set_ylabel('Lick rate [Hz]')
                axis[0][world_idx].set_xlabel(None)
                if world_name == 1:
                    axis[0][world_idx].title.set_text(
                        cage_name + ' / ' + mouse_name + ' - Familiar environment ' + '- last day')
                else:
                    axis[0][world_idx].title.set_text(
                        cage_name + ' / ' + mouse_name + ' - Novel environment ' + '- last day')
                world_table['smooth_lick_rate'].plot(
                    ax=axis[1][world_idx], alpha=1, label=date_name)
            else:
                world_table['smooth_lick_rate'].plot(
                    ax=axis[1][world_idx], alpha=alpha_vals[j], label=date_name)

        j += 1
    START_REWARD, END_REWARD = dict_of_positions[1]
    axis[1][0].axvline(x=START_REWARD / 10, c='red',
                       linewidth=2.5, ls='--', label="reward_zone")
    axis[1][0].axvline(x=END_REWARD / 10, c='red', linewidth=2.5, ls='--')
    START_REWARD, END_REWARD = dict_of_positions[3]
    axis[1][1].axvline(x=START_REWARD / 10, c='red',
                       linewidth=2.5, ls='--', label="reward_zone")
    axis[1][1].axvline(x=END_REWARD / 10, c='red', linewidth=2.5, ls='--')
    axis[0][0].set_ylabel('lick rate [Hz]')
    axis[0][1].set_ylabel(None)
    axis[1][0].set_ylabel('lick rate [Hz]')
    axis[1][1].set_ylabel(None)
    plt.xlabel('Position (cm)')
    axis[1][0].title.set_text(
        cage_name + ' / ' + mouse_name + ' - Familiar environment' + ' - training history')
    axis[1][1].title.set_text(
        cage_name + ' / ' + mouse_name + ' - Novel environment' + ' - training history')
    axis[1][0].legend()
    axis[1][1].legend()
    axis[0][0].legend()
    axis[0][1].legend()
    fig.suptitle("Lick rate plot", fontsize=20, y=0.95)

    save_dir = MICE_TRAINING_DIR + '\\analyzed_data\\plots\\' + \
        cage_name + '\\' + training_date_str + '\\'
    save_file = mouse_name + "_lick_rate_plot_history_stage_F" + '.png'
    if not os.path.isdir(save_dir):
        os.makedirs(save_dir)
    fig.savefig(save_dir + save_file, bbox_inches='tight')
    return


def lick_rate_plot_two_worlds_last_day(data, cage_name, mouse_name, training_date, training_date_str):
    df = data.copy()
    df = df[df['air'] == 1]
    df = df[df['current_World'] != 5]
    df = df[(df['lap_length'] >= MIN_LAP_LENGTH) & (df['lap_length'] <= MAX_LAP_LENGTH)]
    df["world"] = df.groupby(['lap_counter']).current_World.transform('min')
    #  start and end reward zone
    dict_of_positions = get_positions_of_reward_zone(df)

    # generate bin column
    bins_number = BINS_NUMBER  # i.e each bin ~ 1 cm
    window_size = WINDOW_SIZE  # how many bins to average
    labels = np.arange(bins_number)
    df['binned_mm_position'], bins = pd.cut(
        df['position_mm'], bins=bins_number, labels=labels, include_lowest=True, retbins=True)  # binning
    # generate lick per bin and time per bin, both per lap (since we measure time) ,columns
    # contains only good laps so the calculations is good
    group = df.groupby(['lap_counter', 'binned_mm_position'])
    df['right_end_of_bin'] = group['position_mm'].transform(
        'max')  # taking the mm value of the bin
    df['mean_speed_per_bin'] = group['speed'].transform('mean')
    group = df.groupby(['world', 'lap_counter', 'binned_mm_position'])
    df['licks_per_bin_in_lap'] = group['lick_indicator'].transform('sum')
    df['time_in_in_bin_in_lap'] = (group['timeElapsed'].transform(
        max) - group['timeElapsed'].transform(min)) + 0.035
    # unique row per bin per lap per mouse per date
    df = df[['world', 'lap_counter', 'binned_mm_position', 'right_end_of_bin',
             'licks_per_bin_in_lap', 'time_in_in_bin_in_lap']].drop_duplicates()
    # construct data that sum over all laps - just bins is important from now
    group = df.groupby(['world', 'lap_counter', 'binned_mm_position'])
    df['licks_per_bin'] = group['licks_per_bin_in_lap'].transform('sum')
    df['time_in_in_bin'] = group['time_in_in_bin_in_lap'].transform('sum')
    df = df[['lap_counter', 'binned_mm_position', 'right_end_of_bin',
             'licks_per_bin', 'time_in_in_bin']].drop_duplicates()
    df['lick_rate'] = df['licks_per_bin'] / df['time_in_in_bin']

    # sort
    df = df.sort_values(
        ['world', 'lap_counter', 'binned_mm_position'], ascending=[True, False, True])
    #  smoothing the curve
    df['smooth_lick_rate'] = df.groupby(['world', 'lap_counter'])['lick_rate'].transform(
        lambda s: s.rolling(window_size, min_periods=1, center=False).mean())
    df['position_cm'] = df['right_end_of_bin'] / 10
    df['mean_lick_rate_over_laps'] = df.groupby(['binned_mm_position'])[
        'smooth_lick_rate'].transform('mean')
    df = df[df['binned_mm_position'] != 0]  # delete non continues bin
    # plotting

    fig, axis = plt.subplots(1, 2, figsize=(20, 9))
    df.set_index('position_cm', inplace=True)
    world_group = df.groupby('world')
    i = 0
    for world_num, world_table in world_group:
        laps = world_table['lap_counter'].drop_duplicates()
        total_laps = len(laps)
        alpha_vals = np.linspace(0.1, 0.6, total_laps)
        j = 0  # for alpha vals
        lap_groups = world_table.groupby('lap_counter')
        for lap_num, lap_table in lap_groups:
            if j == 0:  # print mean just once
                lap_table['mean_lick_rate_over_laps'].plot(
                    ax=axis[i], alpha=1, c='black', linewidth=3, label='mean_lick_rate')
            lap_table['smooth_lick_rate'].plot(
                ax=axis[i], alpha=alpha_vals[j], label=lap_num)
            j += 1
        i += 1

    START_REWARD, END_REWARD = dict_of_positions[1]
    axis[0].axvline(x=START_REWARD / 10, c='red',
                    linewidth=2.5, ls='--', label="reward_zone")
    axis[0].axvline(x=END_REWARD / 10, c='red', linewidth=2.5, ls='--')
    START_REWARD, END_REWARD = dict_of_positions[3]
    axis[1].axvline(x=START_REWARD / 10, c='red',
                    linewidth=2.5, ls='--', label="reward_zone")
    axis[1].axvline(x=END_REWARD / 10, c='red', linewidth=2.5, ls='--')
    axis[0].set_ylabel('lick rate [Hz]')
    axis[1].set_ylabel(None)
    axis[0].set_xlabel('Position (cm)')
    axis[1].set_xlabel('Position (cm)')
    axis[0].legend()
    axis[1].legend()
    axis[0].title.set_text(cage_name + ' / ' +
                           mouse_name + ' -  Familiar environment')
    axis[1].title.set_text(cage_name + ' / ' +
                           mouse_name + ' - Novel environment')
    fig.suptitle("Lick rate plot - last day", fontsize=20, y=0.95)

    save_dir = MICE_TRAINING_DIR + '\\analyzed_data\\plots\\' + \
        cage_name + '\\' + training_date_str + '\\'
    save_file = mouse_name + "_lick_rate_plot_last_day_stage_F" + '.png'
    if not os.path.isdir(save_dir):
        os.makedirs(save_dir)
    fig.savefig(save_dir + save_file, bbox_inches='tight')

    return


def speed_plot_two_worlds_history(data, cage_name, mouse_name, training_date, training_date_str):
    df = data.copy()
    df = df[df['air'] == 1]
    df = df[df['stage'] >= 3]
    df = df[df['current_World'] != 5]
    df = df[(df['lap_length'] >= MIN_LAP_LENGTH) & (df['lap_length'] <= MAX_LAP_LENGTH)]
    df["world"] = df.groupby(['lap_counter']).current_World.transform('min')
    #  start and end reward zone
    dict_of_positions = get_positions_of_reward_zone(df)

    # generate bin column
    bins_number = BINS_NUMBER  # i.e each bin ~ 1 cm
    window_size = WINDOW_SIZE  # how many bins to average
    labels = np.arange(bins_number)
    df['binned_mm_position'], bins = pd.cut(
        df['position_mm'], bins=bins_number, labels=labels, include_lowest=True, retbins=True)  # binning
    # generate lick per bin and time per bin, both per lap (since we measure time) ,columns
    # contains only good laps so the calculations is good
    group = df.groupby(['date', 'world', 'binned_mm_position'])
    df['right_end_of_bin'] = group['position_mm'].transform(
        'max')  # taking the mm value of the bin
    df['mean_speed_per_bin'] = group['speed'].transform('mean')
    df = df[['date', 'world', 'binned_mm_position',
             'right_end_of_bin', 'mean_speed_per_bin']].drop_duplicates()
    # sort
    df = df.sort_values(['date', 'binned_mm_position'],
                        ascending=[False, True])
    #  smoothing the curve
    df['smooth_speed'] = df.groupby(['date', 'world'])['mean_speed_per_bin'].transform(
        lambda s: s.rolling(window_size, min_periods=1, center=False).mean())
    df['position_cm'] = df['right_end_of_bin'] / 10
    df = df[df['binned_mm_position'] != 0]  # delete non continues bin

    # plotting

    fig, axis = plt.subplots(2, 2, figsize=(20, 9))
    dates = df['date'].drop_duplicates()
    total_dates = len(dates)
    alpha_vals = np.linspace(0.1, 0.6, total_dates)
    j = 0  # for alpha vals
    df.set_index('position_cm', inplace=True)
    date_groups = df.groupby('date')
    for date_name, day_table in date_groups:
        world_group = day_table.groupby('world')
        for world_idx, world_tuple in enumerate(world_group):
            world_name, world_table = world_tuple
            START_REWARD, END_REWARD = dict_of_positions[world_name]
            if date_name == training_date:
                world_table['smooth_speed'].plot(
                    ax=axis[0][world_idx], label='_nolegend_')
                axis[0][world_idx].axvline(
                    x=START_REWARD / 10, c='red', linewidth=2.5, ls='--', label=("reward_zone_" + str(world_name)))
                axis[0][world_idx].axvline(
                    x=END_REWARD / 10, c='red', linewidth=2.5, ls='--')
                axis[0][world_idx].set_ylabel('speed [mm/s]')
                axis[0][world_idx].set_xlabel(None)
                if world_name == 1:
                    axis[0][world_idx].title.set_text(
                        cage_name + ' / ' + mouse_name + ' - Familiar environment ' + '- last day')
                else:
                    axis[0][world_idx].title.set_text(
                        cage_name + ' / ' + mouse_name + ' - Novel environment ' + '- last day')
                world_table['smooth_speed'].plot(
                    ax=axis[1][world_idx], alpha=1, label=date_name)
            else:
                world_table['smooth_speed'].plot(
                    ax=axis[1][world_idx], alpha=alpha_vals[j], label=date_name)

        j += 1
    START_REWARD, END_REWARD = dict_of_positions[1]
    axis[1][0].axvline(x=START_REWARD / 10, c='red',
                       linewidth=2.5, ls='--', label="reward_zone")
    axis[1][0].axvline(x=END_REWARD / 10, c='red', linewidth=2.5, ls='--')
    START_REWARD, END_REWARD = dict_of_positions[3]
    axis[1][1].axvline(x=START_REWARD / 10, c='red',
                       linewidth=2.5, ls='--', label="reward_zone")
    axis[1][1].axvline(x=END_REWARD / 10, c='red', linewidth=2.5, ls='--')
    axis[0][0].set_ylabel('speed [mm/s]')
    axis[0][1].set_ylabel(None)
    axis[1][0].set_ylabel('speed [mm/s]')
    axis[1][1].set_ylabel(None)
    plt.xlabel('Position (cm)')
    axis[1][0].title.set_text(
        cage_name + ' / ' + mouse_name + ' - Familiar environment' + ' - training history')
    axis[1][1].title.set_text(
        cage_name + ' / ' + mouse_name + ' - Novel environment' + ' - training history')
    axis[1][0].legend()
    axis[1][1].legend()
    axis[0][0].legend()
    axis[0][1].legend()
    fig.suptitle("Speed plot", fontsize=20, y=0.95)

    save_dir = MICE_TRAINING_DIR + '\\analyzed_data\\plots\\' + \
        cage_name + '\\' + training_date_str + '\\'
    save_file = mouse_name + "_speed_plot_history_stage_F" + '.png'
    if not os.path.isdir(save_dir):
        os.makedirs(save_dir)
    fig.savefig(save_dir + save_file, bbox_inches='tight')
    return


def speed_plot_two_world_last_day(data, cage_name, mouse_name, training_date, training_date_str):
    df = data.copy()
    df = df[df['air'] == 1]
    df = df[df['current_World'] != 5]
    df = df[(df['lap_length'] >= MIN_LAP_LENGTH) & (df['lap_length'] <= MAX_LAP_LENGTH)]
    df["world"] = df.groupby(['lap_counter']).current_World.transform('min')
    #  start and end reward zone
    dict_of_positions = get_positions_of_reward_zone(df)

    # generate bin column
    bins_number = BINS_NUMBER  # i.e each bin ~ 1 cm
    window_size = WINDOW_SIZE  # how many bins to average
    labels = np.arange(bins_number)
    df['binned_mm_position'], bins = pd.cut(
        df['position_mm'], bins=bins_number, labels=labels, include_lowest=True, retbins=True)  # binning
    # generate lick per bin and time per bin, both per lap (since we measure time) ,columns
    # contains only good laps so the calculations is good
    group = df.groupby(['lap_counter', 'binned_mm_position'])
    df['right_end_of_bin'] = group['position_mm'].transform(
        'max')  # taking the mm value of the bin
    df['mean_speed_per_bin'] = group['speed'].transform('mean')
    df = df[['world', 'lap_counter', 'binned_mm_position',
             'right_end_of_bin', 'mean_speed_per_bin']].drop_duplicates()
    # sort
    df = df.sort_values(
        ['lap_counter', 'binned_mm_position'], ascending=[False, True])
    #  smoothing the curve
    df['smooth_speed'] = df.groupby(['lap_counter'])['mean_speed_per_bin'].transform(
        lambda s: s.rolling(window_size, min_periods=1, center=False).mean())
    df['position_cm'] = df['right_end_of_bin'] / 10
    df['mean_speed_over_laps'] = df.groupby(['binned_mm_position'])[
        'mean_speed_per_bin'].transform('mean')
    df = df[df['binned_mm_position'] != 0]  # delete non continues bin

    # plotting

    fig, axis = plt.subplots(1, 2, figsize=(20, 9))
    df.set_index('position_cm', inplace=True)
    world_group = df.groupby('world')
    i = 0
    for world_num, world_table in world_group:
        laps = world_table['lap_counter'].drop_duplicates()
        total_laps = len(laps)
        alpha_vals = np.linspace(0.1, 0.6, total_laps)
        j = 0  # for alpha vals
        lap_groups = world_table.groupby('lap_counter')
        for lap_num, lap_table in lap_groups:
            if j == 0:  # print mean just once
                lap_table['mean_speed_over_laps'].plot(
                    ax=axis[i], alpha=1, c='black', linewidth=3, label='mean speed')
            lap_table['smooth_speed'].plot(
                ax=axis[i], alpha=alpha_vals[j], label=lap_num)
            j += 1
        i += 1

    START_REWARD, END_REWARD = dict_of_positions[1]
    axis[0].axvline(x=START_REWARD / 10, c='red',
                    linewidth=2.5, ls='--', label="reward_zone")
    axis[0].axvline(x=END_REWARD / 10, c='red', linewidth=2.5, ls='--')
    START_REWARD, END_REWARD = dict_of_positions[3]
    axis[1].axvline(x=START_REWARD / 10, c='red',
                    linewidth=2.5, ls='--', label="reward_zone")
    axis[1].axvline(x=END_REWARD / 10, c='red', linewidth=2.5, ls='--')
    axis[0].set_ylabel('speed [mm/s]')
    axis[1].set_ylabel(None)
    axis[0].set_xlabel('Position (cm)')
    axis[1].set_xlabel('Position (cm)')
    axis[0].legend()
    axis[1].legend()
    axis[0].title.set_text(cage_name + ' / ' +
                           mouse_name + ' -  Familiar environment')
    axis[1].title.set_text(cage_name + ' / ' +
                           mouse_name + ' - Novel environment')
    fig.suptitle("Speed plot - last day", fontsize=20, y=0.95)

    save_dir = MICE_TRAINING_DIR + '\\analyzed_data\\plots\\' + \
        cage_name + '\\' + training_date_str + '\\'
    save_file = mouse_name + "_speed_plot_last_day_stage_F" + '.png'
    if not os.path.isdir(save_dir):
        os.makedirs(save_dir)
    fig.savefig(save_dir + save_file, bbox_inches='tight')

    return


# ## more analytics for stage F

# In[350]:


def running_and_resting_time_multiple_worlds(data):
    """
    assuming that "data" is one mouse df of one training date
    """
    df = data.copy()
    df["world"] = df.groupby(['lap_counter']).current_World.transform('min')
    df['prev_timeElapsed'] = df['timeElapsed'].shift()
    df.fillna(method='bfill', inplace=True)
    df['time_between_frames'] = df['timeElapsed'] - df['prev_timeElapsed']
    df = df[['world', 'time_between_frames', 'air']]
    df['time_per_air_state'] = df.groupby(
        ['air', 'world']).time_between_frames.transform('sum')
    df['time_per_air_state (minutes)'] = (
        (df['time_per_air_state'] / 60) * 1e1).astype(float) / 1e1
    df = df[['world', 'air', 'time_per_air_state (minutes)']].drop_duplicates()
    world_group = df.groupby('world')
    world_dict = {}
    for world_name, world_table in world_group:
        air_on_table = world_table[world_table['air'] == 1]
        air_on = air_on_table.iloc[0]['time_per_air_state (minutes)']
        air_off_table = world_table[world_table['air'] == 0]
        air_off = air_off_table.iloc[0]['time_per_air_state (minutes)']
        total_time = air_on + air_off
        total_time = (int(total_time * 1e2) / 1e2)
        air_on = (int(air_on * 1e2) / 1e2)
        air_off = (int(air_off * 1e2) / 1e2)
        world_dict[world_name] = (air_on, air_off, total_time)
    # output example: {1: (8.2, 2.0, 10.2), 3: (17.42, 2.0, 19.42)}
    return world_dict


def num_of_rewards_per_world(data):
    df = data.copy()
    df["world"] = df.groupby(['lap_counter']).current_World.transform('min')
    df["num_of_rewrads"] = df.groupby(
        ['world']).reward_indicator.transform('sum')
    df = df[['world', 'num_of_rewrads']].drop_duplicates()
    world_group = df.groupby('world')
    world_dict = {}
    for world_name, world_table in world_group:
        world_dict[world_name] = world_table.iloc[0]["num_of_rewrads"]
    return world_dict  # example of output: {1: 7, 3: 9}


def lap_duration_stage_F(data, training_date, cage_name, mouse_name, training_date_str):
    df = data.copy()
    df = df[df['air'] == 1]
    df = df[df['stage'] >= 3]
    df = df[df['current_World'] != 5]

    df["world"] = df.groupby(['lap_counter']).current_World.transform('min')
    group = df.groupby(['date', 'lap_counter', 'world'])
    df['lap_duration'] = group['timeElapsed'].transform(
        max) - group['timeElapsed'].transform(min)
    df = df[["world", "date", "lap_counter", "lap_duration"]].drop_duplicates()
    df["avg_lap_duration_per_world_per_date"] = df.groupby(
        ['date', 'world'])['lap_duration'].transform('mean')
    df = df[["date", "world", "avg_lap_duration_per_world_per_date"]
            ].drop_duplicates()
    df = df.sort_values(['date'], ascending=[True])
    plot_lap_duration_per_date_per_world(
        df, cage_name, mouse_name, training_date_str)
    today = df[df["date"] == training_date]
    world_group = today.groupby('world')
    world_dict = {}
    for world_name, world_table in world_group:
        average_lap_duration = int(
            (world_table.iloc[0]["avg_lap_duration_per_world_per_date"]) * 1e2) / 1e2
        world_dict[world_name] = average_lap_duration
    return world_dict


def plot_lap_duration_per_date_per_world(data, cage_name, mouse_name, training_date_str):
    df = data.copy()
    world_group = df.groupby('world')
    for world_name, world_table in world_group:
        # world_table["avg_lap_duration_per_world_per_date"]
        fig, axis = plt.subplots(2, 1, figsize=(20, 9))
        world_table.plot(
            x="date", y="avg_lap_duration_per_world_per_date", ax=axis[0], label='_nolegend_')
        axis[0].set_xlabel("Date")
        axis[0].set_ylabel("Mean lap duration [s]")
        axis[0].title.set_text(cage_name + "/" + mouse_name + "_world_number_" + str(world_name) +
                               " - Mean lap duration over training")
        # extract last week data
        range_max = world_table["date"].max()
        range_min = range_max - dt.timedelta(days=7)
        df = world_table[(world_table['date'] >= range_min) &
                         (world_table['date'] <= range_max)]

        df.plot(x="date", y="avg_lap_duration_per_world_per_date",
                ax=axis[1], label='_nolegend_')
        axis[1].set_xlabel("Date")
        axis[1].set_ylabel("Mean lap duration [s]")
        axis[1].title.set_text(cage_name + "/" + mouse_name + "_world_number_" + str(world_name) +
                               " - Mean lap duration - last week")
        fig.tight_layout()
        fig.suptitle("Mean lap duration over training - world number " +
                     str(world_name), fontsize=20, y=1.02)

        save_dir = MICE_TRAINING_DIR + '\\analyzed_data\\plots\\' + \
            cage_name + '\\' + training_date_str + '\\'
        save_file = mouse_name + "_lap_duration_plot_world_number_" + \
            str(world_name) + '.png'
        if not os.path.isdir(save_dir):
            os.makedirs(save_dir)
        fig.savefig(save_dir + save_file, bbox_inches='tight')
    return


# ## daily for stage F

# In[397]:


def generate_daily_update_stage_F(results, cage_name, mouse_name, weight, baseline_weight, training_date, stage, training_date_str):
    current_percent = (float(weight) / float(baseline_weight)) * 100
    current_percent = (int(current_percent * 1e2) / 1e2)
    eighty_percent = (baseline_weight * 0.8)
    eighty_percent = (int(eighty_percent * 1e2) / 1e2)
    day = str(training_date.day)
    month = str(training_date.month)
    year = str(training_date.year)[2:]
    training_date = day + '.' + month + '.' + year
    save_dir = MICE_TRAINING_DIR + '\\analyzed_data\\daily_updates\\'
    file_path = save_dir + training_date + '.txt'
    if not os.path.isfile(file_path):
        with open(file_path, 'w+', newline='') as f:
            f.write("Good afternoon:)\n\n")
            f.write("Below are training statistics from " +
                    training_date + ':\n\n')

            f.write(
                "    Reminder: Stage F is the first time Novel environment is introduced to the mouse." + ':\n\n')

    with open(file_path, 'a', newline='') as f:
        world_air_time_dict = results[0]
        world_rewards_num_dict = results[1]
        lap_duration_dict = results[2]

        air_on_fam, air_off_fam, total_time_fam = world_air_time_dict[1]
        air_on_nov, air_off_nov, total_time_nov = world_air_time_dict[3]
        training_duration = total_time_fam + total_time_nov
        total_rewards = world_rewards_num_dict[3] + world_rewards_num_dict[1]

        f.write(cage_name + " / " + mouse_name + ":\n")
        f.write("1. Weight: " + str(weight) + " i.e " + str(current_percent) +
                "% from its baseline." + " (80% from its baseline is: " + str(eighty_percent) + ")\n")
        f.write("2. Training stage: " + stage + "\n")
        f.write("3. Toal Duration of training: " +
                str(training_duration) + " minutes" + "\n")
        f.write("4. Duration of Familiar env: " +
                str(total_time_fam) + " minutes" + "\n")
        f.write("5. Duration of Novel env: " +
                str(total_time_nov) + " minutes" + "\n")
        f.write("6. Average lap duration Familiar env: " +
                str(lap_duration_dict[1]) + "seconds" + "\n")
        f.write("7. Average lap duration Novel env: " +
                str(lap_duration_dict[3]) + "seconds" + "\n")
        f.write("8. Number of rewards in Familiar env: " +
                str(world_rewards_num_dict[1]) + "\n")
        f.write("9. Number of rewards in Novel env: " +
                str(world_rewards_num_dict[3]) + "\n")
        f.write("10. Total number of rewards: " + str(total_rewards) + "\n")
        f.write("    Reminder: the rewards number equal to the number of laps." + "\n")
        f.write("\n")
    return


# # stage C-D-E analytics

# In[327]:


def stage_CDE_analytics(data, cage_name, mouse_name, training_date, training_date_str):
    df = data.copy()
    df = df[df["name"] == mouse_name]
    df = df[df["lap_counter"] >= 0]
    average_lap_duration = lap_duration(
        df, training_date, cage_name, mouse_name, training_date_str)
    virmen_unit_speed_plot_one_world_history(
        df, cage_name, mouse_name, training_date, training_date_str)
    virmen_unit_lick_rate_plot_one_world_history(
        df, cage_name, mouse_name, training_date, training_date_str)
    virmen_unit_lick_number_plot_one_world_history(
        df, cage_name, mouse_name, training_date, training_date_str)
    df = df[df["date"] == training_date]
    virmen_unit_speed_plot_one_world_last_day(
        df, cage_name, mouse_name, training_date, training_date_str)
    virmen_unit_lick_rate_plot_one_world_last_day(
        df, cage_name, mouse_name, training_date, training_date_str)


    # speed_plot_one_world_history(
    #     df, cage_name, mouse_name, training_date, training_date_str)
    # lick_rate_plot_one_world_history(
    #     df, cage_name, mouse_name, training_date, training_date_str)
    # df = df[df["date"] == training_date]
    # speed_plot_one_world_last_day(
    #     df, cage_name, mouse_name, training_date, training_date_str)
    # lick_rate_plot_one_world_last_day(
    #     df, cage_name, mouse_name, training_date, training_date_str)
    air_on, air_off, total_time = running_and_resting_time(df)
    num_of_rewrads = df["reward_indicator"].sum()
    num_of_laps = df["lap_counter"].max() + 1  # since start from 0
    return num_of_laps, num_of_rewrads, air_on, air_off, total_time, average_lap_duration

# In[323]:


def lap_duration(data, training_date, cage_name, mouse_name, training_date_str):
    df = data.copy()
    df = df[df['air'] == 1]
    df = df[df['stage'] >= 3]
    df = df[df['current_World'] != 5]
    group = df.groupby(['date', 'lap_counter'])
    df['lap_duration'] = group['timeElapsed'].transform(
        max) - group['timeElapsed'].transform(min)
    df = df[["date", "lap_counter", "lap_duration"]].drop_duplicates()
    df["avg_lap_duration_per_date"] = df.groupby(
        'date')['lap_duration'].transform('mean')
    df = df[["date", "avg_lap_duration_per_date"]].drop_duplicates()
    df = df.sort_values(['date'], ascending=[True])
    plot_lap_duration_per_date(df, cage_name, mouse_name, training_date_str)
    today = df[df["date"] == training_date]
    average_lap_duration = int(
        (today.iloc[0]["avg_lap_duration_per_date"]) * 1e2) / 1e2
    return average_lap_duration


def plot_lap_duration_per_date(data, cage_name, mouse_name, training_date_str):
    df = data.copy()
    fig, axis = plt.subplots(2, 1, figsize=(20, 9))
    df.plot(x="date", y="avg_lap_duration_per_date",
            ax=axis[0], label='_nolegend_')
    axis[0].set_xlabel("Date")
    axis[0].set_ylabel("Mean lap duration [s]")
    axis[0].title.set_text(cage_name + "/" + mouse_name +
                           " - Mean lap duration over training")

    # extract last week data
    range_max = df["date"].max()
    range_min = range_max - dt.timedelta(days=7)
    df = df[(df['date'] >= range_min) & (df['date'] <= range_max)]

    df.plot(x="date", y="avg_lap_duration_per_date",
            ax=axis[1], label='_nolegend_')
    axis[1].set_xlabel("Date")
    axis[1].set_ylabel("Mean lap duration [s]")
    axis[1].title.set_text(cage_name + "/" + mouse_name +
                           " - Mean lap duration - last week")

    fig.tight_layout()
    fig.suptitle("Mean Lap Duration", fontsize=20, y=1.02)

    save_dir = MICE_TRAINING_DIR + '\\analyzed_data\\plots\\' + \
        cage_name + '\\' + training_date_str + '\\'
    save_file = mouse_name + "_lap_duration_plot" + '.png'
    if not os.path.isdir(save_dir):
        os.makedirs(save_dir)
    fig.savefig(save_dir + save_file, bbox_inches='tight')
    return


# ## speed plot - for C-D-E stages

# In[356]:

def virmen_unit_speed_plot_one_world_history(data, cage_name, mouse_name, training_date, training_date_str):
    df = data.copy()
    df = df[df['air'] == 1]
    df = df[df['stage'] >= 3]
    df = df[df['current_World'] != 5]
    df = df[(df['lap_length'] >= MIN_LAP_LENGTH) & (df['lap_length'] <= MAX_LAP_LENGTH)]
    # the max is just for extract the value, since we have only one world
    current_world = df["current_World"].drop_duplicates().max()
    #  start and end reward zone
    dift_of_positions = get_positions_of_reward_zone(df)
    # START_REWARD, END_REWARD = dift_of_positions[current_world]
    START_REWARD, END_REWARD = 1070, 1280
    # generate bin column
    # bins_number = BINS_NUMBER  # i.e each bin ~ 1 cm
    window_size = WINDOW_SIZE  # how many bins to average

    # generate bin - reward zone isolated
    max_virmen_position = df['position'].max()
    start_track_interval = pd.interval_range(
        start=START_VIRNMEN_POSTION, end=START_GIVE_REWARD)
    reward_interval = pd.interval_range(
        start=START_GIVE_REWARD, end=(START_GIVE_REWARD + 4))
    end_track_interval = pd.interval_range(
        start=(START_GIVE_REWARD + 4), end=max_virmen_position)
    temp_interval = start_track_interval.union(reward_interval)
    interval_bins = temp_interval.union(end_track_interval)
    labels = np.arange(len(interval_bins))
    df['binned_position'], bins = pd.cut(
        df['position'], bins=interval_bins, labels=labels, include_lowest=True, retbins=True)  # binning
    # generate lick per bin and time per bin, both per lap (since we measure time) ,columns
    # contains only good laps so the calculations is good
    group = df.groupby(['date', 'binned_position'])
    df['right_end_of_bin'] = group['position'].transform(
        'max')  # taking the mm value of the bin
    df['mean_speed_per_bin'] = group['speed'].transform('mean')
    df = df[['date', 'binned_position', 'right_end_of_bin',
             'mean_speed_per_bin']].drop_duplicates()
    # sort
    df = df.sort_values(['date', 'binned_position'],
                        ascending=[False, True])
    #  smoothing the curve
    df['smooth_speed'] = df.groupby(['date'])['mean_speed_per_bin'].transform(
        lambda s: s.rolling(window_size, min_periods=1, center=False).mean())
    df['position_cm'] = df['right_end_of_bin']
    df = df[df['binned_position'] != 0]  # delete non continues bin

    # plotting

    fig, axis = plt.subplots(2, 1, figsize=(20, 9))
    dates = df['date'].drop_duplicates()
    total_dates = len(dates)
    alpha_vals = np.linspace(0.1, 1, total_dates)
    j = 0  # for alpha vals
    df.set_index('position_cm', inplace=True)
    date_groups = df.groupby('date')
    for date_name, day_table in date_groups:
        if date_name == training_date:
            day_table['smooth_speed'].plot(ax=axis[0], label='_nolegend_')
            axis[0].axvline(x=START_REWARD / 10, c='red',
                            linewidth=2.5, ls='--', label="reward_zone")
            axis[0].axvline(x=END_REWARD / 10, c='red', linewidth=2.5, ls='--')
            axis[0].set_ylabel('speed [mm/s]')
            axis[0].set_xlabel(None)
            axis[0].title.set_text(
                cage_name + ' ' + mouse_name + ' - last day')
        day_table['smooth_speed'].plot(
            ax=axis[1], alpha=alpha_vals[j], label=date_name)
        j += 1
    axis[1].axvline(x=START_REWARD / 10, c='red',
                    linewidth=2.5, ls='--', label="reward_zone")
    axis[1].axvline(x=END_REWARD / 10, c='red', linewidth=2.5, ls='--')
    axis[1].set_ylabel('speed [mm/s]')
    axis[1].set_xlabel(None)
    axis[1].title.set_text(
        cage_name + '/ ' + mouse_name + ' - training history')
    axis[0].legend()
    axis[1].legend()
    plt.xlabel("virmen unit (a.u)")
    fig.suptitle("Speed plot", fontsize=20, y=0.95)

    save_dir = MICE_TRAINING_DIR + '\\analyzed_data\\plots\\' + \
        cage_name + '\\' + training_date_str + '\\'
    save_file = mouse_name + "_speed_plot_history" + '.png'
    if not os.path.isdir(save_dir):
        os.makedirs(save_dir)
    fig.savefig(save_dir + save_file, bbox_inches='tight')
    return


def speed_plot_one_world_history(data, cage_name, mouse_name, training_date, training_date_str):
    df = data.copy()
    df = df[df['air'] == 1]
    df = df[df['stage'] >= 3]
    df = df[df['current_World'] != 5]
    df = df[(df['lap_length'] >= MIN_LAP_LENGTH) & (df['lap_length'] <= MAX_LAP_LENGTH)]
    # the max is just for extract the value, since we have only one world
    current_world = df["current_World"].drop_duplicates().max()
    #  start and end reward zone
    dift_of_positions = get_positions_of_reward_zone(df)
    START_REWARD, END_REWARD = dift_of_positions[current_world]

    # generate bin column
    # bins_number = BINS_NUMBER  # i.e each bin ~ 1 cm
    window_size = WINDOW_SIZE  # how many bins to average

    # generate bin - reward zone isolated
    max_virmen_position = df['position'].max()
    start_track_interval = pd.interval_range(
        start=START_VIRNMEN_POSTION, end=START_GIVE_REWARD)
    reward_interval = pd.interval_range(
        start=START_GIVE_REWARD, end=(START_GIVE_REWARD + 4))
    end_track_interval = pd.interval_range(
        start=(START_GIVE_REWARD + 4), end=max_virmen_position)
    temp_interval = start_track_interval.union(reward_interval)
    interval_bins = temp_interval.union(end_track_interval)
    labels = np.arange(len(interval_bins))
    df['binned_position'], bins = pd.cut(
        df['position'], bins=interval_bins, labels=labels, include_lowest=True, retbins=True)  # binning
    # generate lick per bin and time per bin, both per lap (since we measure time) ,columns
    # contains only good laps so the calculations is good
    group = df.groupby(['date', 'binned_position'])
    df['right_end_of_bin'] = group['position_mm'].transform(
        'max')  # taking the mm value of the bin
    df['mean_speed_per_bin'] = group['speed'].transform('mean')
    df = df[['date', 'binned_position', 'right_end_of_bin',
             'mean_speed_per_bin']].drop_duplicates()
    # sort
    df = df.sort_values(['date', 'binned_position'],
                        ascending=[False, True])
    #  smoothing the curve
    df['smooth_speed'] = df.groupby(['date'])['mean_speed_per_bin'].transform(
        lambda s: s.rolling(window_size, min_periods=1, center=False).mean())
    df['position_cm'] = df['right_end_of_bin'] / 10
    df = df[df['binned_position'] != 0]  # delete non continues bin

    # plotting

    fig, axis = plt.subplots(2, 1, figsize=(20, 9))
    dates = df['date'].drop_duplicates()
    total_dates = len(dates)
    alpha_vals = np.linspace(0.1, 1, total_dates)
    j = 0  # for alpha vals
    df.set_index('position_cm', inplace=True)
    date_groups = df.groupby('date')
    for date_name, day_table in date_groups:
        if date_name == training_date:
            day_table['smooth_speed'].plot(ax=axis[0], label='_nolegend_')
            axis[0].axvline(x=START_REWARD / 10, c='red',
                            linewidth=2.5, ls='--', label="reward_zone")
            axis[0].axvline(x=END_REWARD / 10, c='red', linewidth=2.5, ls='--')
            axis[0].set_ylabel('speed [mm/s]')
            axis[0].set_xlabel(None)
            axis[0].title.set_text(
                cage_name + ' ' + mouse_name + ' - last day')
        day_table['smooth_speed'].plot(
            ax=axis[1], alpha=alpha_vals[j], label=date_name)
        j += 1
    axis[1].axvline(x=START_REWARD / 10, c='red',
                    linewidth=2.5, ls='--', label="reward_zone")
    axis[1].axvline(x=END_REWARD / 10, c='red', linewidth=2.5, ls='--')
    axis[1].set_ylabel('speed [mm/s]')
    axis[1].set_xlabel(None)
    axis[1].title.set_text(
        cage_name + '/ ' + mouse_name + ' - training history')
    axis[0].legend()
    axis[1].legend()
    plt.xlabel("Position (cm)")
    fig.suptitle("Speed plot", fontsize=20, y=0.95)

    save_dir = MICE_TRAINING_DIR + '\\analyzed_data\\plots\\' + \
        cage_name + '\\' + training_date_str + '\\'
    save_file = mouse_name + "_speed_plot_history" + '.png'
    if not os.path.isdir(save_dir):
        os.makedirs(save_dir)
    fig.savefig(save_dir + save_file, bbox_inches='tight')
    return


def virmen_unit_speed_plot_one_world_last_day(data, cage_name, mouse_name, training_date, training_date_str):
    df = data.copy()
    df = df[df['air'] == 1]
    df = df[df['current_World'] != 5]
    df = df[(df['lap_length'] >= MIN_LAP_LENGTH) & (df['lap_length'] <= MAX_LAP_LENGTH)]
    # the max is just for extract the value, since we have only one world
    current_world = df["current_World"].drop_duplicates().max()
    #  start and end reward zone
    dift_of_positions = get_positions_of_reward_zone(df)
    # START_REWARD_not_used, END_REWARD = dift_of_positions[current_world]
    START_REWARD, END_REWARD = 1070, 1280
    # for last day plot - take the reward start position just from the last day data
    #dff = df.copy()
    #dff = dff[dff["reward"] == 1]
    #dff["start_rwd"] = dff.groupby(
    #    ['lap_counter']).position.transform('min')
    #START_REWARD = dff["start_rwd"].min()
    # generate bin - reward zone isolated
    window_size = WINDOW_SIZE  # how many bins to average
    max_virmen_position = df['position'].max()
    start_track_interval = pd.interval_range(
        start=START_VIRNMEN_POSTION, end=START_GIVE_REWARD)
    reward_interval = pd.interval_range(
        start=START_GIVE_REWARD, end=(START_GIVE_REWARD + 4))
    end_track_interval = pd.interval_range(
        start=(START_GIVE_REWARD + 4), end=max_virmen_position)
    temp_interval = start_track_interval.union(reward_interval)
    interval_bins = temp_interval.union(end_track_interval)
    labels = np.arange(len(interval_bins))
    df['binned_position'], bins = pd.cut(
        df['position'], bins=interval_bins, labels=labels, include_lowest=True, retbins=True)  # binning

    # generate lick per bin and time per bin, both per lap (since we measure time) ,columns
    # contains only good laps so the calculations is good
    group = df.groupby(['lap_counter', 'binned_position'])
    df['right_end_of_bin'] = group['position'].transform(
        'max')  # taking the mm value of the bin
    df['mean_speed_per_bin'] = group['speed'].transform('mean')
    df = df[['lap_counter', 'binned_position',
             'right_end_of_bin', 'mean_speed_per_bin']].drop_duplicates()
    # sort
    df = df.sort_values(
        ['lap_counter', 'binned_position'], ascending=[False, True])
    #  smoothing the curve
    df['smooth_speed'] = df.groupby(['lap_counter'])['mean_speed_per_bin'].transform(
        lambda s: s.rolling(window_size, min_periods=1, center=False).mean())
    df['position_cm'] = df['right_end_of_bin']
    df['mean_speed_over_laps'] = df.groupby(['binned_position'])[
        'mean_speed_per_bin'].transform('mean')
    df = df[df['binned_position'] != 0]  # delete non continues bin

    # plotting

    fig, axis = plt.subplots(1, 1, figsize=(20, 9))
    laps = df['lap_counter'].drop_duplicates()
    total_laps = len(laps)
    alpha_vals = np.linspace(0.1, 0.6, total_laps)
    j = 0  # for alpha vals
    df.set_index('position_cm', inplace=True)
    lap_groups = df.groupby('lap_counter')
    for lap_num, lap_table in lap_groups:
        if j == 0:  # print mean just once
            lap_table['mean_speed_over_laps'].plot(
                ax=axis, alpha=1, c='black', linewidth=3, label='mean speed')
        lap_table['smooth_speed'].plot(
            ax=axis, alpha=alpha_vals[j], label='_nolegend_')
        j += 1
    axis.axvline(x=START_REWARD / 10, c='red',
                 linewidth=2.5, ls='--', label="reward_zone")
    axis.axvline(x=END_REWARD / 10, c='red', linewidth=2.5, ls='--')
    axis.set_ylabel('speed [mm/s]')
    axis.set_xlabel(None)
    axis.title.set_text(cage_name + '/ ' + mouse_name)
    axis.legend()
    plt.xlabel("virmen unit (a.u)")
    fig.suptitle("Speed during each lap - last day", fontsize=20, y=0.95)

    save_dir = MICE_TRAINING_DIR + '\\analyzed_data\\plots\\' + \
        cage_name + '\\' + training_date_str + '\\'
    save_file = mouse_name + "_speed_plot_last_day" + '.png'
    if not os.path.isdir(save_dir):
        os.makedirs(save_dir)
    fig.savefig(save_dir + save_file, bbox_inches='tight')
    return


def speed_plot_one_world_last_day(data, cage_name, mouse_name, training_date, training_date_str):
    df = data.copy()
    df = df[df['air'] == 1]
    df = df[df['current_World'] != 5]
    df = df[(df['lap_length'] >= MIN_LAP_LENGTH) & (df['lap_length'] <= MAX_LAP_LENGTH)]
    # the max is just for extract the value, since we have only one world
    current_world = df["current_World"].drop_duplicates().max()
    #  start and end reward zone
    dift_of_positions = get_positions_of_reward_zone(df)
    START_REWARD_not_used, END_REWARD = dift_of_positions[current_world]
    # for last day plot - take the reward start position just from the last day data
    dff = df.copy()
    dff = dff[dff["reward"] == 1]
    dff["start_rwd_mm"] = dff.groupby(
        ['lap_counter']).position_mm.transform('min')
    START_REWARD = dff["start_rwd_mm"].min()
    # generate bin - reward zone isolated
    window_size = WINDOW_SIZE  # how many bins to average
    max_virmen_position = df['position'].max()
    start_track_interval = pd.interval_range(
        start=START_VIRNMEN_POSTION, end=START_GIVE_REWARD)
    reward_interval = pd.interval_range(
        start=START_GIVE_REWARD, end=(START_GIVE_REWARD + 4))
    end_track_interval = pd.interval_range(
        start=(START_GIVE_REWARD + 4), end=max_virmen_position)
    temp_interval = start_track_interval.union(reward_interval)
    interval_bins = temp_interval.union(end_track_interval)
    labels = np.arange(len(interval_bins))
    df['binned_position'], bins = pd.cut(
        df['position'], bins=interval_bins, labels=labels, include_lowest=True, retbins=True)  # binning

    # generate lick per bin and time per bin, both per lap (since we measure time) ,columns
    # contains only good laps so the calculations is good
    group = df.groupby(['lap_counter', 'binned_position'])
    df['right_end_of_bin'] = group['position_mm'].transform(
        'max')  # taking the mm value of the bin
    df['mean_speed_per_bin'] = group['speed'].transform('mean')
    df = df[['lap_counter', 'binned_position',
             'right_end_of_bin', 'mean_speed_per_bin']].drop_duplicates()
    # sort
    df = df.sort_values(
        ['lap_counter', 'binned_position'], ascending=[False, True])
    #  smoothing the curve
    df['smooth_speed'] = df.groupby(['lap_counter'])['mean_speed_per_bin'].transform(
        lambda s: s.rolling(window_size, min_periods=1, center=False).mean())
    df['position_cm'] = df['right_end_of_bin'] / 10
    df['mean_speed_over_laps'] = df.groupby(['binned_position'])[
        'mean_speed_per_bin'].transform('mean')
    df = df[df['binned_position'] != 0]  # delete non continues bin

    # plotting

    fig, axis = plt.subplots(1, 1, figsize=(20, 9))
    laps = df['lap_counter'].drop_duplicates()
    total_laps = len(laps)
    alpha_vals = np.linspace(0.1, 0.6, total_laps)
    j = 0  # for alpha vals
    df.set_index('position_cm', inplace=True)
    lap_groups = df.groupby('lap_counter')
    for lap_num, lap_table in lap_groups:
        if j == 0:  # print mean just once
            lap_table['mean_speed_over_laps'].plot(
                ax=axis, alpha=1, c='black', linewidth=3, label='mean speed')
        lap_table['smooth_speed'].plot(
            ax=axis, alpha=alpha_vals[j], label='_nolegend_')
        j += 1
    axis.axvline(x=START_REWARD / 10, c='red',
                 linewidth=2.5, ls='--', label="reward_zone")
    axis.axvline(x=END_REWARD / 10, c='red', linewidth=2.5, ls='--')
    axis.set_ylabel('speed [mm/s]')
    axis.set_xlabel(None)
    axis.title.set_text(cage_name + '/ ' + mouse_name)
    axis.legend()
    plt.xlabel("Position (cm)")
    fig.suptitle("Speed during each lap - last day", fontsize=20, y=0.95)

    save_dir = MICE_TRAINING_DIR + '\\analyzed_data\\plots\\' + \
        cage_name + '\\' + training_date_str + '\\'
    save_file = mouse_name + "_speed_plot_last_day" + '.png'
    if not os.path.isdir(save_dir):
        os.makedirs(save_dir)
    fig.savefig(save_dir + save_file, bbox_inches='tight')
    return


def virmen_unit_lick_rate_plot_one_world_history(data, cage_name, mouse_name, training_date, training_date_str):
    df = data.copy()
    df = df[df['air'] == 1]
    df = df[df['stage'] >= 3]
    df = df[df['current_World'] != 5]
    df = df[(df['lap_length'] >= MIN_LAP_LENGTH) & (df['lap_length'] <= MAX_LAP_LENGTH)]
    # the max is just for extract the value, since we have only one world
    current_world = df["current_World"].drop_duplicates().max()
    #  start and end reward zone
    dift_of_positions = get_positions_of_reward_zone(df)
    # START_REWARD, END_REWARD = dift_of_positions[current_world]
    START_REWARD, END_REWARD = 1070, 1280

    # generate bin - reward zone isolated
    window_size = WINDOW_SIZE  # how many bins to average
    max_virmen_position = df['position'].max()
    start_track_interval = pd.interval_range(
        start=START_VIRNMEN_POSTION, end=START_GIVE_REWARD)
    reward_interval = pd.interval_range(
        start=START_GIVE_REWARD, end=(START_GIVE_REWARD + 4))
    end_track_interval = pd.interval_range(
        start=(START_GIVE_REWARD + 4), end=max_virmen_position)
    temp_interval = start_track_interval.union(reward_interval)
    interval_bins = temp_interval.union(end_track_interval)
    labels = np.arange(len(interval_bins))
    df['binned_position'], bins = pd.cut(
        df['position'], bins=interval_bins, labels=labels, include_lowest=True, retbins=True)  # binning

    # generate lick per bin and time per bin, both per lap (since we measure time) ,columns
    # contains only good laps so the calculations is good
    group = df.groupby(['date', 'binned_position'])
    df['right_end_of_bin'] = group['position'].transform(
        'max')  # taking the mm value of the bin
    df['mean_speed_per_bin'] = group['speed'].transform('mean')
    group = df.groupby(['date', 'lap_counter', 'binned_position'])
    df['licks_per_bin_in_lap'] = group['lick_indicator'].transform('sum')
    df['time_in_in_bin_in_lap'] = (group['timeElapsed'].transform(
        max) - group['timeElapsed'].transform(min)) + 0.035
    df['lick_rate_in_lap_in_bin'] = df['licks_per_bin_in_lap'] / df['time_in_in_bin_in_lap']

    # unique row per bin per lap per mouse per date
    df = df[['date', 'lap_counter', 'binned_position', 'right_end_of_bin',
            'lick_rate_in_lap_in_bin']].drop_duplicates()
    # construct data that sum over all laps - just bins is important from now
    group = df.groupby(['date', 'binned_position'])
    df['lick_rate'] = group['lick_rate_in_lap_in_bin'].transform('mean')
    df = df[['date', 'binned_position', 'right_end_of_bin',
                'lick_rate']].drop_duplicates()

    # sort
    df = df.sort_values(['date', 'binned_position'],
                        ascending=[False, True])
    #  smoothing the curve
    df['smooth_lick_rate'] = df.groupby(['date'])['lick_rate'].transform(
        lambda s: s.rolling(window_size, min_periods=1, center=False).mean())
    df['position_cm'] = df['right_end_of_bin']
    df = df[df['binned_position'] != 0]  # delete non continues bin

    # plotting

    fig, axis = plt.subplots(2, 1, figsize=(20, 9))
    dates = df['date'].drop_duplicates()
    total_dates = len(dates)
    alpha_vals = np.linspace(0.1, 1, total_dates)
    j = 0  # for alpha vals
    df.set_index('position_cm', inplace=True)
    date_groups = df.groupby('date')
    for date_name, day_table in date_groups:
        if date_name == training_date:
            day_table['smooth_lick_rate'].plot(ax=axis[0], label='_nolegend_')
            axis[0].axvline(x=START_REWARD / 10, c='red',
                            linewidth=2.5, ls='--', label="reward_zone")
            axis[0].axvline(x=END_REWARD / 10, c='red', linewidth=2.5, ls='--')
            axis[0].set_ylabel('lick rate [Hz]')
            axis[0].set_xlabel(None)
            axis[0].title.set_text(
                cage_name + ' ' + mouse_name + ' - last day')
        day_table['smooth_lick_rate'].plot(
            ax=axis[1], alpha=alpha_vals[j], label=date_name)
        j += 1
    axis[1].axvline(x=START_REWARD / 10, c='red',
                    linewidth=2.5, ls='--', label="reward_zone")
    axis[1].axvline(x=END_REWARD / 10, c='red', linewidth=2.5, ls='--')
    axis[1].set_ylabel('lick rate [Hz]')
    axis[1].set_xlabel(None)
    axis[1].title.set_text(
        cage_name + '/ ' + mouse_name + ' - training history')
    axis[0].legend()
    axis[1].legend()
    plt.xlabel("virmen unit (a.u)")
    fig.suptitle("Lick rate plot", fontsize=20, y=0.95)

    save_dir = MICE_TRAINING_DIR + '\\analyzed_data\\plots\\' + \
        cage_name + '\\' + training_date_str + '\\'
    save_file = mouse_name + "_lick_rate_plot_history" + '.png'
    if not os.path.isdir(save_dir):
        os.makedirs(save_dir)
    fig.savefig(save_dir + save_file, bbox_inches='tight')
    return

def virmen_unit_lick_number_plot_one_world_history(data, cage_name, mouse_name, training_date, training_date_str):
    df = data.copy()
    df = df[df['air'] == 1]
    df = df[df['stage'] >= 3]
    df = df[df['current_World'] != 5]
    df = df[(df['lap_length'] >= MIN_LAP_LENGTH) & (df['lap_length'] <= MAX_LAP_LENGTH)]
    # the max is just for extract the value, since we have only one world
    current_world = df["current_World"].drop_duplicates().max()
    #  start and end reward zone
    dift_of_positions = get_positions_of_reward_zone(df)
    # START_REWARD, END_REWARD = dift_of_positions[current_world]
    START_REWARD, END_REWARD = 1070, 1280

    # generate bin - reward zone isolated
    window_size = WINDOW_SIZE  # how many bins to average
    max_virmen_position = df['position'].max()
    start_track_interval = pd.interval_range(
        start=START_VIRNMEN_POSTION, end=START_GIVE_REWARD)
    reward_interval = pd.interval_range(
        start=START_GIVE_REWARD, end=(START_GIVE_REWARD + 4))
    end_track_interval = pd.interval_range(
        start=(START_GIVE_REWARD + 4), end=max_virmen_position)
    temp_interval = start_track_interval.union(reward_interval)
    interval_bins = temp_interval.union(end_track_interval)
    labels = np.arange(len(interval_bins))
    df['binned_position'], bins = pd.cut(
        df['position'], bins=interval_bins, labels=labels, include_lowest=True, retbins=True)  # binning

    # generate lick per bin and time per bin, both per lap (since we measure time) ,columns
    # contains only good laps so the calculations is good
    group = df.groupby(['date', 'binned_position'])
    df['right_end_of_bin'] = group['position'].transform(
        'max')  # taking the mm value of the bin
    df['mean_speed_per_bin'] = group['speed'].transform('mean')
    group = df.groupby(['date', 'lap_counter', 'binned_position'])
    df['licks_per_bin_in_lap'] = group['lick_indicator'].transform('sum')
    df['time_in_in_bin_in_lap'] = (group['timeElapsed'].transform(
        max) - group['timeElapsed'].transform(min)) + 0.035
    df['lick_number_in_lap_in_bin'] = df['licks_per_bin_in_lap'] 

    # unique row per bin per lap per mouse per date
    df = df[['date', 'lap_counter', 'binned_position', 'right_end_of_bin',
            'lick_number_in_lap_in_bin']].drop_duplicates()
    # construct data that sum over all laps - just bins is important from now
    group = df.groupby(['date', 'binned_position'])
    df['lick_number'] = group['lick_number_in_lap_in_bin'].transform('mean')
    df = df[['date', 'binned_position', 'right_end_of_bin',
                'lick_number']].drop_duplicates()

    # sort
    df = df.sort_values(['date', 'binned_position'],
                        ascending=[False, True])
    #  smoothing the curve
    df['smooth_lick_number'] = df.groupby(['date'])['lick_number'].transform(
        lambda s: s.rolling(window_size, min_periods=1, center=False).mean())
    df['position_cm'] = df['right_end_of_bin']
    df = df[df['binned_position'] != 0]  # delete non continues bin

    # plotting

    fig, axis = plt.subplots(2, 1, figsize=(20, 9))
    dates = df['date'].drop_duplicates()
    total_dates = len(dates)
    alpha_vals = np.linspace(0.1, 1, total_dates)
    j = 0  # for alpha vals
    df.set_index('position_cm', inplace=True)
    date_groups = df.groupby('date')
    for date_name, day_table in date_groups:
        if date_name == training_date:
            day_table['smooth_lick_number'].plot(ax=axis[0], label='_nolegend_')
            axis[0].axvline(x=START_REWARD / 10, c='red',
                            linewidth=2.5, ls='--', label="reward_zone")
            axis[0].axvline(x=END_REWARD / 10, c='red', linewidth=2.5, ls='--')
            axis[0].set_ylabel('number of licks')
            axis[0].set_xlabel(None)
            axis[0].title.set_text(
                cage_name + ' ' + mouse_name + ' - last day')
        day_table['smooth_lick_number'].plot(
            ax=axis[1], alpha=alpha_vals[j], label=date_name)
        j += 1
    axis[1].axvline(x=START_REWARD / 10, c='red',
                    linewidth=2.5, ls='--', label="reward_zone")
    axis[1].axvline(x=END_REWARD / 10, c='red', linewidth=2.5, ls='--')
    axis[1].set_ylabel('number of licks')
    axis[1].set_xlabel(None)
    axis[1].title.set_text(
        cage_name + '/ ' + mouse_name + ' - training history')
    axis[0].legend()
    axis[1].legend()
    plt.xlabel("virmen unit (a.u)")
    fig.suptitle("number of licks plot", fontsize=20, y=0.95)

    save_dir = MICE_TRAINING_DIR + '\\analyzed_data\\plots\\' + \
        cage_name + '\\' + training_date_str + '\\'
    save_file = mouse_name + "_lick_number_plot_history" + '.png'
    if not os.path.isdir(save_dir):
        os.makedirs(save_dir)
    fig.savefig(save_dir + save_file, bbox_inches='tight')
    return

# In[ ]: lick rate

def lick_rate_plot_one_world_history(data, cage_name, mouse_name, training_date, training_date_str):
    df = data.copy()
    df = df[df['air'] == 1]
    df = df[df['stage'] >= 3]
    df = df[df['current_World'] != 5]
    df = df[(df['lap_length'] >= MIN_LAP_LENGTH) & (df['lap_length'] <= MAX_LAP_LENGTH)]
    # the max is just for extract the value, since we have only one world
    current_world = df["current_World"].drop_duplicates().max()
    #  start and end reward zone
    dift_of_positions = get_positions_of_reward_zone(df)
    START_REWARD, END_REWARD = dift_of_positions[current_world]

    # generate bin - reward zone isolated
    window_size = WINDOW_SIZE  # how many bins to average
    max_virmen_position = df['position'].max()
    start_track_interval = pd.interval_range(
        start=START_VIRNMEN_POSTION, end=START_GIVE_REWARD)
    reward_interval = pd.interval_range(
        start=START_GIVE_REWARD, end=(START_GIVE_REWARD + 4))
    end_track_interval = pd.interval_range(
        start=(START_GIVE_REWARD + 4), end=max_virmen_position)
    temp_interval = start_track_interval.union(reward_interval)
    interval_bins = temp_interval.union(end_track_interval)
    labels = np.arange(len(interval_bins))
    df['binned_position'], bins = pd.cut(
        df['position'], bins=interval_bins, labels=labels, include_lowest=True, retbins=True)  # binning

    # generate lick per bin and time per bin, both per lap (since we measure time) ,columns
    # contains only good laps so the calculations is good
    group = df.groupby(['date', 'binned_position'])
    df['right_end_of_bin'] = group['position_mm'].transform(
        'max')  # taking the mm value of the bin
    df['mean_speed_per_bin'] = group['speed'].transform('mean')
    group = df.groupby(['date', 'lap_counter', 'binned_position'])
    df['licks_per_bin_in_lap'] = group['lick_indicator'].transform('sum')
    df['time_in_in_bin_in_lap'] = (group['timeElapsed'].transform(
        max) - group['timeElapsed'].transform(min)) + 0.035
    # unique row per bin per lap per mouse per date
    df = df[['date', 'lap_counter', 'binned_position', 'right_end_of_bin',
             'licks_per_bin_in_lap', 'time_in_in_bin_in_lap']].drop_duplicates()
    # construct data that sum over all laps - just bins is important from now
    group = df.groupby(['date', 'binned_position'])
    df['licks_per_bin'] = group['licks_per_bin_in_lap'].transform('sum')
    df['time_in_in_bin'] = group['time_in_in_bin_in_lap'].transform('sum')
    df = df[['date', 'binned_position', 'right_end_of_bin',
             'licks_per_bin', 'time_in_in_bin']].drop_duplicates()
    df['lick_rate'] = df['licks_per_bin'] / df['time_in_in_bin']

    # sort
    df = df.sort_values(['date', 'binned_position'],
                        ascending=[False, True])
    #  smoothing the curve
    df['smooth_lick_rate'] = df.groupby(['date'])['lick_rate'].transform(
        lambda s: s.rolling(window_size, min_periods=1, center=False).mean())
    df['position_cm'] = df['right_end_of_bin'] / 10
    df = df[df['binned_position'] != 0]  # delete non continues bin

    # plotting

    fig, axis = plt.subplots(2, 1, figsize=(20, 9))
    dates = df['date'].drop_duplicates()
    total_dates = len(dates)
    alpha_vals = np.linspace(0.1, 1, total_dates)
    j = 0  # for alpha vals
    df.set_index('position_cm', inplace=True)
    date_groups = df.groupby('date')
    for date_name, day_table in date_groups:
        if date_name == training_date:
            day_table['smooth_lick_rate'].plot(ax=axis[0], label='_nolegend_')
            axis[0].axvline(x=START_REWARD / 10, c='red',
                            linewidth=2.5, ls='--', label="reward_zone")
            axis[0].axvline(x=END_REWARD / 10, c='red', linewidth=2.5, ls='--')
            axis[0].set_ylabel('lick rate [Hz]')
            axis[0].set_xlabel(None)
            axis[0].title.set_text(
                cage_name + ' ' + mouse_name + ' - last day')
        day_table['smooth_lick_rate'].plot(
            ax=axis[1], alpha=alpha_vals[j], label=date_name)
        j += 1
    axis[1].axvline(x=START_REWARD / 10, c='red',
                    linewidth=2.5, ls='--', label="reward_zone")
    axis[1].axvline(x=END_REWARD / 10, c='red', linewidth=2.5, ls='--')
    axis[1].set_ylabel('lick rate [Hz]')
    axis[1].set_xlabel(None)
    axis[1].title.set_text(
        cage_name + '/ ' + mouse_name + ' - training history')
    axis[0].legend()
    axis[1].legend()
    plt.xlabel("Position (cm)")
    fig.suptitle("Lick rate plot", fontsize=20, y=0.95)

    save_dir = MICE_TRAINING_DIR + '\\analyzed_data\\plots\\' + \
        cage_name + '\\' + training_date_str + '\\'
    save_file = mouse_name + "_lick_rate_plot_history" + '.png'
    if not os.path.isdir(save_dir):
        os.makedirs(save_dir)
    fig.savefig(save_dir + save_file, bbox_inches='tight')
    return


def virmen_unit_lick_rate_plot_one_world_last_day(data, cage_name, mouse_name, training_date, training_date_str):
    df = data.copy()
    df = df[df['air'] == 1]
    df = df[df['current_World'] != 5]
    df = df[(df['lap_length'] >= MIN_LAP_LENGTH) & (df['lap_length'] <= MAX_LAP_LENGTH)]
    # the max is just for extract the value, since we have only one world
    current_world = df["current_World"].drop_duplicates().max()
    #  start and end reward zone
    dift_of_positions = get_positions_of_reward_zone(df)
    # START_REWARD_not_used, END_REWARD = dift_of_positions[current_world]
    START_REWARD, END_REWARD = 1070, 1280

    # generate bin - reward zone isolated
    window_size = WINDOW_SIZE  # how many bins to average
    max_virmen_position = df['position'].max()
    start_track_interval = pd.interval_range(
        start=START_VIRNMEN_POSTION, end=START_GIVE_REWARD)
    reward_interval = pd.interval_range(
        start=START_GIVE_REWARD, end=(START_GIVE_REWARD + 4))
    end_track_interval = pd.interval_range(
        start=(START_GIVE_REWARD + 4), end=max_virmen_position)
    temp_interval = start_track_interval.union(reward_interval)
    interval_bins = temp_interval.union(end_track_interval)
    labels = np.arange(len(interval_bins))
    df['binned_position'], bins = pd.cut(
        df['position'], bins=interval_bins, labels=labels, include_lowest=True, retbins=True)  # binning
    # generate lick per bin and time per bin, both per lap (since we measure time) ,columns
    # contains only good laps so the calculations is good
    group = df.groupby(['binned_position'])
    df['right_end_of_bin'] = group['position'].transform(
        'max')  # taking the mm value of the bin
    df['mean_speed_per_bin'] = group['speed'].transform('mean')
    group = df.groupby(['lap_counter', 'binned_position'])
    df['licks_per_bin_in_lap'] = group['lick_indicator'].transform('sum')
    df['time_in_in_bin_in_lap'] = (group['timeElapsed'].transform(
        max) - group['timeElapsed'].transform(min)) + 0.035
    # unique row per bin per lap per mouse per date
    df = df[['lap_counter', 'binned_position', 'right_end_of_bin',
             'licks_per_bin_in_lap', 'time_in_in_bin_in_lap']].drop_duplicates()
    # construct data that sum over all laps - just bins is important from now
    group = df.groupby(['lap_counter', 'binned_position'])
    df['licks_per_bin'] = group['licks_per_bin_in_lap'].transform('sum')
    df['time_in_in_bin'] = group['time_in_in_bin_in_lap'].transform('sum')
    df = df[['lap_counter', 'binned_position', 'right_end_of_bin',
             'licks_per_bin', 'time_in_in_bin']].drop_duplicates()
    df['lick_rate'] = df['licks_per_bin'] / df['time_in_in_bin']

    # sort
    df = df.sort_values(
        ['lap_counter', 'binned_position'], ascending=[False, True])
    #  smoothing the curve
    df['smooth_lick_rate'] = df.groupby(['lap_counter'])['lick_rate'].transform(
        lambda s: s.rolling(window_size, min_periods=1, center=False).mean())
    df['position_cm'] = df['right_end_of_bin']
    df['mean_lick_rate_over_laps'] = df.groupby(['binned_position'])[
        'smooth_lick_rate'].transform('mean')
    df = df[df['binned_position'] != 0]  # delete non continues bin
    # plotting

    fig, axis = plt.subplots(1, 1, figsize=(20, 9))
    laps = df['lap_counter'].drop_duplicates()
    total_laps = len(laps)
    alpha_vals = np.linspace(0.1, 0.6, total_laps)
    j = 0  # for alpha vals
    df.set_index('position_cm', inplace=True)
    lap_groups = df.groupby('lap_counter')
    for lap_num, lap_table in lap_groups:
        if j == 0:  # print mean just once
            lap_table['mean_lick_rate_over_laps'].plot(
                ax=axis, alpha=1, c='black', linewidth=3, label='mean lick rate')
        lap_table['smooth_lick_rate'].plot(
            ax=axis, alpha=alpha_vals[j], label='_nolegend_')
        j += 1
    axis.axvline(x=START_REWARD / 10, c='red',
                 linewidth=2.5, ls='--', label="reward_zone")
    axis.axvline(x=END_REWARD / 10, c='red', linewidth=2.5, ls='--')
    axis.set_ylabel('lick rate [Hz]')
    axis.set_xlabel(None)
    axis.title.set_text(cage_name + '/ ' + mouse_name)
    axis.legend()
    plt.xlabel("virmen unit (a.u)")
    fig.suptitle("lick rate per each lap - last day", fontsize=20, y=0.95)

    save_dir = MICE_TRAINING_DIR + '\\analyzed_data\\plots\\' + \
        cage_name + '\\' + training_date_str + '\\'
    save_file = mouse_name + "_lick_rate_plot_last_day" + '.png'
    if not os.path.isdir(save_dir):
        os.makedirs(save_dir)
    fig.savefig(save_dir + save_file, bbox_inches='tight')
    return


def lick_rate_plot_one_world_last_day(data, cage_name, mouse_name, training_date, training_date_str):
    df = data.copy()
    df = df[df['air'] == 1]
    df = df[df['current_World'] != 5]
    df = df[(df['lap_length'] >= MIN_LAP_LENGTH) & (df['lap_length'] <= MAX_LAP_LENGTH)]
    # the max is just for extract the value, since we have only one world
    current_world = df["current_World"].drop_duplicates().max()
    #  start and end reward zone
    dift_of_positions = get_positions_of_reward_zone(df)
    START_REWARD_not_used, END_REWARD = dift_of_positions[current_world]
    # for last day plot - take the reward start position just from the last day data
    dff = df.copy()
    dff = dff[dff["reward"] == 1]
    dff["start_rwd_mm"] = dff.groupby(
        ['lap_counter']).position_mm.transform('min')
    START_REWARD = dff["start_rwd_mm"].min()
    # generate bin - reward zone isolated
    window_size = WINDOW_SIZE  # how many bins to average
    max_virmen_position = df['position'].max()
    start_track_interval = pd.interval_range(
        start=START_VIRNMEN_POSTION, end=START_GIVE_REWARD)
    reward_interval = pd.interval_range(
        start=START_GIVE_REWARD, end=(START_GIVE_REWARD + 4))
    end_track_interval = pd.interval_range(
        start=(START_GIVE_REWARD + 4), end=max_virmen_position)
    temp_interval = start_track_interval.union(reward_interval)
    interval_bins = temp_interval.union(end_track_interval)
    labels = np.arange(len(interval_bins))
    df['binned_position'], bins = pd.cut(
        df['position'], bins=interval_bins, labels=labels, include_lowest=True, retbins=True)  # binning
    # generate lick per bin and time per bin, both per lap (since we measure time) ,columns
    # contains only good laps so the calculations is good
    group = df.groupby(['binned_position'])
    df['right_end_of_bin'] = group['position_mm'].transform(
        'max')  # taking the mm value of the bin
    df['mean_speed_per_bin'] = group['speed'].transform('mean')
    group = df.groupby(['lap_counter', 'binned_position'])
    df['licks_per_bin_in_lap'] = group['lick_indicator'].transform('sum')
    df['time_in_in_bin_in_lap'] = (group['timeElapsed'].transform(
        max) - group['timeElapsed'].transform(min)) + 0.035
    # unique row per bin per lap per mouse per date
    df = df[['lap_counter', 'binned_position', 'right_end_of_bin',
             'licks_per_bin_in_lap', 'time_in_in_bin_in_lap']].drop_duplicates()
    # construct data that sum over all laps - just bins is important from now
    group = df.groupby(['lap_counter', 'binned_position'])
    df['licks_per_bin'] = group['licks_per_bin_in_lap'].transform('sum')
    df['time_in_in_bin'] = group['time_in_in_bin_in_lap'].transform('sum')
    df = df[['lap_counter', 'binned_position', 'right_end_of_bin',
             'licks_per_bin', 'time_in_in_bin']].drop_duplicates()
    df['lick_rate'] = df['licks_per_bin'] / df['time_in_in_bin']

    # sort
    df = df.sort_values(
        ['lap_counter', 'binned_position'], ascending=[False, True])
    #  smoothing the curve
    df['smooth_lick_rate'] = df.groupby(['lap_counter'])['lick_rate'].transform(
        lambda s: s.rolling(window_size, min_periods=1, center=False).mean())
    df['position_cm'] = df['right_end_of_bin'] / 10
    df['mean_lick_rate_over_laps'] = df.groupby(['binned_position'])[
        'smooth_lick_rate'].transform('mean')
    df = df[df['binned_position'] != 0]  # delete non continues bin
    # plotting

    fig, axis = plt.subplots(1, 1, figsize=(20, 9))
    laps = df['lap_counter'].drop_duplicates()
    total_laps = len(laps)
    alpha_vals = np.linspace(0.1, 0.6, total_laps)
    j = 0  # for alpha vals
    df.set_index('position_cm', inplace=True)
    lap_groups = df.groupby('lap_counter')
    for lap_num, lap_table in lap_groups:
        if j == 0:  # print mean just once
            lap_table['mean_lick_rate_over_laps'].plot(
                ax=axis, alpha=1, c='black', linewidth=3, label='mean lick rate')
        lap_table['smooth_lick_rate'].plot(
            ax=axis, alpha=alpha_vals[j], label='_nolegend_')
        j += 1
    axis.axvline(x=START_REWARD / 10, c='red',
                 linewidth=2.5, ls='--', label="reward_zone")
    axis.axvline(x=END_REWARD / 10, c='red', linewidth=2.5, ls='--')
    axis.set_ylabel('lick rate [Hz]')
    axis.set_xlabel(None)
    axis.title.set_text(cage_name + '/ ' + mouse_name)
    axis.legend()
    plt.xlabel("Position (cm)")
    fig.suptitle("lick rate per each lap - last day", fontsize=20, y=0.95)

    save_dir = MICE_TRAINING_DIR + '\\analyzed_data\\plots\\' + \
        cage_name + '\\' + training_date_str + '\\'
    save_file = mouse_name + "_lick_rate_plot_last_day" + '.png'
    if not os.path.isdir(save_dir):
        os.makedirs(save_dir)
    fig.savefig(save_dir + save_file, bbox_inches='tight')
    return

# []


def generate_daily_update_stage_CDE(results, cage_name, mouse_name, weight, baseline_weight, training_date_date_format, stage, training_date_str):
    try:
        current_percent = (float(weight) / float(baseline_weight)) * 100
    except:
        print("if it is a new cage make sure that the weight table is updated")
        print("remember, the first raw is the baseline weight.")
        print("in addition, make sure that the csv delimiter is commoas and not tabs")
        return
    current_percent = (int(current_percent * 1e2) / 1e2)
    eighty_percent = (baseline_weight * 0.8)
    eighty_percent = (int(eighty_percent * 1e2) / 1e2)
    day = str(training_date_date_format.day)
    month = str(training_date_date_format.month)
    year = str(training_date_date_format.year)[2:]
    training_date = day + '.' + month + '.' + year
    save_dir = MICE_TRAINING_DIR + '\\analyzed_data\\daily_updates\\'
    file_path = save_dir + training_date + '.txt'
    if not os.path.isfile(file_path):
        with open(file_path, 'w+', newline='') as f:
            f.write("Good afternoon:)\n\n")
            f.write("Below are training statistics from " +
                    training_date + ':\n\n')

            f.write(
                "    Reminder: the difference between C,D,E is the running duration between resting time." + "\n")
            f.write(
                "          – C is 8 on 2 off, D is 4 / 2 and E is 2 / 2 ." + "\n\n")

    with open(file_path, 'a', newline='') as f:
        num_of_laps, num_of_rewrads, air_on = results[0], results[1], results[2]
        air_off, total_time, average_lap_duration = results[3], results[4], results[5]
        average_lap_duration = (int(average_lap_duration * 1e2) / 1e2)
        f.write(cage_name + " / " + mouse_name + ":\n")
        f.write("1. Weight: " + str(weight) + " i.e " + str(current_percent) +
                "% from its baseline." + " (80% from its baseline is: " + str(eighty_percent) + ")\n")
        f.write("2. Training stage: " + stage + "\n")
        f.write("3. Duration of training: " +
                str(total_time) + " minutes" + "\n")
        f.write("4. Duration of running: " + str(air_on) + " minutes" + "\n")
        f.write("5. Duration of resting: " + str(air_off) + " minutes" + "\n")
        f.write("6. Average lap duration: " +
                str(average_lap_duration) + " seconds" + "\n")
        f.write("7. Number of rewards: " + str(num_of_rewrads) + "\n")
        f.write("   Reminder: the rewards number equal to the number of laps." + "\n")
        f.write("\n")
    return


# # stage B analytics
#

# In[ ]:


def stage_B_analytics(data, cage_name, mouse_name, training_date):
    df = data.copy()
    df = df[df["name"] == mouse_name]
    df = df[df["date"] == training_date]
    air_on, air_off, total_time = running_and_resting_time(df)
    num_of_rewrads = df["reward_indicator"].sum()
    df = df[df['air'].astype(int) == 1]
    max_speed = df["speed"].max()
    avg_speed = df["speed"].mean()
    return num_of_rewrads, max_speed, avg_speed, air_on, air_off, total_time


# In[207]:


def generate_daily_update_stage_B(results, cage_name, mouse_name, weight, baseline_weight, training_date_date_format):
    eighty_percent = (baseline_weight * 0.8)
    eighty_percent = (int(eighty_percent * 1e2) / 1e2)
    day = str(training_date_date_format.day)
    month = str(training_date_date_format.month)
    year = str(training_date_date_format.year)[2:]
    training_date = day + '.' + month + '.' + year
    save_dir = MICE_TRAINING_DIR + '\\analyzed_data\\daily_updates\\'
    file_path = save_dir + training_date + '.txt'
    if not os.path.isfile(file_path):
        with open(file_path, 'w+', newline='') as f:
            f.write("Good afternoon:)\n\n")
            f.write("Below are training statistics from " +
                    training_date + ':\n\n')
    with open(file_path, 'a', newline='') as f:
        num_of_rewrads, max_speed, avg_speed = results[0], results[1], results[2]
        air_on, air_off, total_time = results[3], results[4], results[5]
        f.write(cage_name + " / " + mouse_name + ":\n")
        f.write("1. Weight: " + str(weight) +
                " (While 80% from its baseline is: " + str(eighty_percent) + ")\n")
        f.write("2. Training stage: " + 'B' + "\n")
        f.write("    Reminder: running with white screen, rewards when running above an increasing speed threshold" + "\n")
        f.write("    – with delay of 3s between rewards." + "\n")
        f.write("3. Duration of training: " +
                str(total_time) + " minutes" + "\n")
        f.write("4. Duration of running: " + str(air_on) + " minutes" + "\n")
        f.write("5. Duration of resting: " + str(air_off) + " minutes" + "\n")
        f.write("6. Maximun speed: " + str(max_speed) + "\n")
        f.write("7. Average speed: " + str(avg_speed) + " seconds" + "\n")
        f.write("8. Number of rewards: " + str(num_of_rewrads) + "\n")
        f.write("\n")
    return


# # Send daily mail

# In[208]:


def send_daily_mail(cage_name, training_date_date_format):

    day = str(training_date_date_format.day)
    month = str(training_date_date_format.month)
    year = str(training_date_date_format.year)[2:]
    training_date = day + '.' + month + '.' + year
    save_dir = MICE_TRAINING_DIR + '\\analyzed_data\\daily_updates\\'
    output_file = save_dir + training_date + '.txt'
    pdf_file = MICE_TRAINING_DIR + "\\analyzed_data\\plots\\" + \
        cage_name + '\\' + training_date + '\\' + 'daily_plots.pdf'
    subject = 'Daily Training Update: ' + \
        str(training_date_date_format.today())
    mails_to_send = ['enteryormailhere1',
                     'enteryormailhere2', 'enteryormailhere3']
    me = 'enteryormailhere-sender'

    msg = MIMEMultipart()

    # the text file contains only ASCII characters.
    with open(output_file, 'rt') as fp:
        # Create a text/plain message
        txt_msg = MIMEText(fp.read())

    msg.attach(txt_msg)
    with open(pdf_file, "rb") as fil:
        part = MIMEApplication(
            fil.read(),
            Name=basename(pdf_file)
        )

    part['Content-Disposition'] = 'attachment; filename="%s"' % basename(
        pdf_file)
    msg.attach(part)

    msg['Subject'] = subject
    msg['From'] = me
    msg['To'] = ', '.join(mails_to_send)

    gmail_user = 'the sender mail'
    gmail_password = 'the sender password'
    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.ehlo()
    server.login(gmail_user, gmail_password)
    server.sendmail(me, mails_to_send, msg.as_string())
    server.close()


# # main

# In[398]:

def generate_daily_pdf(cage_name, training_date_str):
    mypath = MICE_TRAINING_DIR + "\\analyzed_data\\plots\\" + \
        cage_name + '\\' + training_date_str
    output_path = mypath + "\\" + "daily_plots.pdf"
    imagelist = [f for f in listdir(mypath) if isfile(join(mypath, f))]
    pdf = FPDF(orientation='L', unit='mm', format='A3')
    mouse_names = []
    for image in imagelist:
        mouse_name = image.split('_')[0]
        if mouse_name not in mouse_names:
            mouse_names.append(mouse_name)
            pdf.add_page()
            pdf.set_font('Arial', '', 40)
            pdf.write(260, '                                             ' +
                      cage_name + '/' + mouse_name)
        pdf.add_page()
        pdf.image(mypath + '\\' + image, w=400, h=250)
    pdf.output(output_path, "F")
    return


def main():
    # df of: data, cage, name. stage, weight
    config_data = read_training_meta_data()
    date_groups = config_data.groupby('date')
    for training_date, day_table in date_groups:
        day = str(training_date.day)
        month = str(training_date.month)
        year = str(training_date.year)[2:]
        training_date_str = day + '.' + month + '.' + year
        cage_groups = day_table.groupby('cage')
        for cage_name, cage_table in cage_groups:
            mouse_groups = cage_table.groupby('name')
            cage_data = build_data_table([cage_name])
            for mouse_name, mouse_data in mouse_groups:
                # per mouse:
                # 1. read baseline weight
                # 2. update weight in weight tracking table
                # 3. calc appropriate analytics (stage dependent)
                # 4. generate daily txt file
                baseline_weight = read_baseline(mouse_name, cage_name)
                update_weight(cage_name, mouse_name, training_date,
                              mouse_data.iloc[0]["weight"])  # update weight table
                calc_analytics(cage_data, cage_name, mouse_name, training_date, training_date_str,
                               mouse_data.iloc[0]["stage"], mouse_data.iloc[0]["weight"], baseline_weight)
            generate_daily_pdf(cage_name, training_date_str)
            send_daily_mail(cage_name, training_date)
    return


def test_read_training_meta_data():
    # read metadata_table from virmen, extract not analyzed rows and mark them as analyzed
    file_path = MICE_TRAINING_DIR + \
        "\helper_data_tabels\\test_training_metadata_from_virmen.csv"
    # This will hold our information for later (since we can't both read and write simultaneously)
    new_file = []
    header = ''
    mice_list = []
    with open(file_path, 'rt') as f:
        reader = csv.reader(f, delimiter=',')
        for i, line in enumerate(reader):
            # append all lines to the new file
            # but change the anlyzed value to 1
            if i == 0:
                header = line
                new_file.append(line)
                continue
            if len(line) == 0:
                continue
            if line[5] == '0':  # not analyzed data
                mice_list.append(line[0:5])
                new_line = line[0:5] + [0]
                new_file.append(new_line)
            else:
                new_file.append(line)
    with open(file_path, 'w', newline='') as f:
        writer = csv.writer(f, delimiter=',')
        for line in new_file:    # Write all of our new information back into the new file.
            writer.writerow(line)
    config_data = pd.DataFrame(mice_list, columns=header[0:5])
    # data, cage, name. stage, weight; just of not analyzed data
    config_data['date'] = pd.to_datetime(config_data['date'], dayfirst=True)
    config_data['date'] = config_data['date'].dt.date
    return config_data


def test_main():
    # df of: data, cage, name. stage, weight
    config_data = test_read_training_meta_data()
    date_groups = config_data.groupby('date')
    for training_date, day_table in date_groups:
        day = str(training_date.day)
        month = str(training_date.month)
        year = str(training_date.year)[2:]
        training_date_str = day + '.' + month + '.' + year
        cage_groups = day_table.groupby('cage')
        for cage_name, cage_table in cage_groups:
            mouse_groups = cage_table.groupby('name')
            cage_data = build_data_table([cage_name])
            for mouse_name, mouse_data in mouse_groups:
                # per mouse:
                # 1. read baseline weight
                # 2. update weight in weight tracking table
                # 3. calc appropriate analytics (stage dependent)
                # 4. generate daily txt file
                baseline_weight = read_baseline(mouse_name, cage_name)
                # update_weight(cage_name, mouse_name, training_date,
                #   mouse_data.iloc[0]["weight"])  # update weight table
                # calc_analytics(cage_data, cage_name, mouse_name, training_date, training_date_str,
                #    mouse_data.iloc[0]["stage"], mouse_data.iloc[0]["weight"], baseline_weight)
            # generate_daily_pdf(cage_name, training_date_str)
            send_daily_mail(cage_name, training_date)
    return


# test_main()
main()

# %%
