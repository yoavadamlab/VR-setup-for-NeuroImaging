function code = Mice_training_wheel
% Begin header code - DO NOT EDIT
code.initialization = @initializationCodeFun;
code.runtime = @runtimeCodeFun;
code.termination = @terminationCodeFun;
% End header code - DO NOT EDIT
end

% --- INITIALIZATION code: executes before the ViRMEn engine starts.
function vr = initializationCodeFun(vr)
% Hardware parameters 
global ARDUINO_COM_PORT LOCAL_TRACKING_DIR;
ARDUINO_COM_PORT = 'COM5'; 
LOCAL_TRACKING_DIR = 'C:\Users\owner\Desktop\ViRMEn 2016-02-12\Tracking\';
% default params to GUI
cage = 'OP10';
mouse = 'X';
rounds = '4';
to_save = 'no';

% user input configuration 
[vr.experimentEnded, vr.imaging_session, vr.imaging_time] = training_or_imaging();
[vr.stage, vr.experimentEnded] = user_input_stage();
if vr.experimentEnded
    return
end
vr.stage_number = get_stage_number(vr.stage);
% open dialog for get user input
try 
    [vr.cage_name, vr.mouse_name, vr.weight, vr.save_data, vr.training_round_number] = user_input(cage, mouse, rounds, to_save);
catch ME % press cancel on the dialog box
    disp(ME);
    vr.experimentEnded = true;
    vr.stage = 'None';
    return
end

% initialization of serial port for Arduino virmen connection (bi-directional)
vr.arduino_port = serialport(ARDUINO_COM_PORT,9600);
configureTerminator(vr.arduino_port,"CR/LF");
flush(vr.arduino_port);
vr.arduino_port.UserData = struct("mov", 0 ,"lick",0, "trigger", 0);
configureCallback(vr.arduino_port,"terminator",@read_arduino_packet);

% if there are problems with th connection - look at older version
% of mice_training and try clean the buffer we did there

% start of lap and end of lap positions in Virmen units
% those coordinates will be common for all worlds
vr.start_position_y = -30;
vr.end_position_y = 162;
vr.position(2) = vr.start_position_y; % initial mouse vr position
vr.basic_world = 1;
vr.black_screen = 5; 
vr.white_screen = 6;
vr.nov_env = 3;

%initializing data table for saving training data
% and return its path
if ~vr.imaging_session
    [vr.path, vr.date_path] = initialize_data_table(); 
end

% set the wheel radius
vr.r = 70; % mm
vr.n_wheel_sripes = 90;
vr.wheel_spin = 0;
vr.last_wheel_spin = 0;
vr.p_revolution = 400; % in one revolution the rotary encoder increment up to 200 
% variables from arduino
vr.arduino_lick_counter = 0;
vr.last_arduino_lick_counter = 0;
% variables to arduino
vr.reward_signal = 1;
vr.start_session_signal = 2;
vr.end_session_signal = 3;

% vr struct data members initialization - set all to zero
[vr.wheel_spin_counter, vr.lap_counter, vr.cur_angle, vr.trigger, vr.speed] = deal(0);
[vr.angle, vr.prev_angle ,vr.speed ,vr.direction ,vr.distance, vr.mouse_movement, vr.cum_movement] = deal(0);
vr.first_iteration = true;
vr.resting_flag = false; % equivalent to air on
vr.last_time_point = vr.timeElapsed;
% boolean variables - inputs from arduino system (air valve, lick detector, reward valve)
[vr.lick ,vr.reward, vr.lap_diff, vr.reward_counter, vr.lick_counter] = deal(0);
vr.got_reward = false;
[vr.running_time, vr.resting_time] = timer_configurations(vr);
vr.start_round = true; % round = running + resting time
vr.lap_end = false;
vr.lick_print_flag = true;
vr.lap_end_iter = -5; % arbitrary minus number 
vr.lap_end_flag = true;
vr.start_resting = 0;
vr.time_elapsed_round = 0;

% configuration for stage B
vr.reward_time = 0;
vr.speed_limit = 50; 
vr.minimum_speed_limit = 50;
vr.reward_dealy = 2; % 2 s delay between rewards
vr.last_speed_limit_change = 0;
vr.rewards_from_last_change = 0;

% configuration for Stage F (remapping)
vr.round_counter = 0;
vr.rounds_before_novel_env = 2;
vr.nov_env_lap_counter = 0;
vr.laps_before_nov = 2; % after "rounds_before_novel_env " rounds, wait few laps before remap
% for imaging_session
vr.start_synchronization_clock = false;
vr.imaging_session_number = 0;
vr.saved_imaging_session = false;
vr.cumsum_lap_length = 0;
[vr.time_from_trigger,vr.image_path] = deal(0); % will set to be clock in imaging session

% set the initial worlds
vr.currentWorld = stage_control(vr);
[vr.start_reward_zone, vr.end_reward_zone] = get_reward_cords(vr.currentWorld);
display("Starting stage " + vr.stage);
vr.start_session_time = datetime('now');
display("Start time : " + datestr(vr.start_session_time, 'HH:MM:ss'));

% start session by sending a signal to arduino for zeroing counters
write(vr.arduino_port,vr.start_session_signal, 'int64');
end

% --- RUNTIME code: executes on every iteration of the ViRMEn engine.
function vr = runtimeCodeFun(vr)
% start control
[vr.start_round , vr.time_elapsed_round, vr.first_iteration] = start_round_control(vr);

% calculation of mouse movement 
[vr.last_wheel_spin, vr.mouse_movement, vr.speed, vr.cumsum_lap_length, vr.last_time_point] = movement_calc(vr);
 
%lick detector
[vr.last_arduino_lick_counter, vr.lick, vr.lick_counter] = lick_control(vr);

% give reward when enter to the reward zone
[vr.got_reward, vr.reward_counter, vr.reward] = reward_control(vr);

% if get reward in stage B start timer for next reward
[vr.speed_limit, vr.last_speed_limit_change, vr.rewards_from_last_change, ...
vr.reward_time, vr.got_reward] = stage_b_speed_control(vr);

% check if lap ended
[vr.lap_end, vr.lap_diff] = end_of_lap_control(vr.stage, vr.position(2), vr.start_position_y, vr.end_position_y);

% check if round ended
[vr.got_reward, vr.currentWorld, vr.start_resting, vr.round_counter, ...
vr.start_round, vr.resting_flag, vr.lap_end_flag, vr.lap_end_iter] = end_of_round_conrol(vr);

% teleport at the end of lap
[vr.lap_end, vr.lap_end_flag, vr.currentWorld, vr.start_reward_zone, vr.end_reward_zone ...
, vr.position(2), vr.dp(:), vr.lap_counter, vr.nov_env_lap_counter, vr.cumsum_lap_length] = telaportation_control(vr);


% after rich training duration & end of lap
[vr.training_round_number, vr.experimentEnded] = check_if_training_finshed(vr);

% save data to csv
save_iteration_data(vr);

% imaging session control
[vr.saved_imaging_session, vr.experimentEnded, vr.imaging_time, vr.trigger, vr.time_from_trigger, ...
vr.imaging_session_number, vr.currentWorld, vr.position(2), vr.dp(:), vr.image_path, vr.date_path] = imaging_control(vr);

[vr.start_synchronization_clock, vr.currentWorld, vr.saved_imaging_session, vr.start_round] =  end_imaging_session(vr);
end

% --- TERMINATION code: executes after the ViRMEn engine stops.
function vr = terminationCodeFun(vr)
configureCallback(vr.arduino_port, "off");
%write(vr.arduino_port,vr.end_session_signal, 'int64');
if strcmp(vr.stage, 'Test water drop') || strcmp(vr.stage, 'None')
    return
end
try
if vr.save_data && ~ vr.imaging_session
    % save data from training
    tracking_dir = 'path to training_data dir \';
    mouse_dir = strcat(tracking_dir, vr.cage_name,'\',vr.mouse_name);
    a = string(day(vr.date_path));
    b = string(month(vr.date_path));
    c = extractBetween(string(year(vr.date_path)),3,4);
    date_format = strcat(a,'.',b,'.',c);
    file_name = strcat(mouse_dir,'\',date_format, '.csv' );
    try
        copyfile(vr.path, file_name, 'f');
    catch 
        mkdir(mouse_dir);
        copyfile(vr.path, file_name, 'f');
    end
    % save configurations
    daily_dir = 'path to helper_data_tabels dir\';
    config_table = strcat(daily_dir, 'training_metadata_from_virmen.csv');
    M = readmatrix(config_table, 'OutputType','char');
    last_training_data = {date_format vr.cage_name vr.mouse_name vr.stage vr.weight '0'};
    % to make areas appear in first column
    M = [M;last_training_data ];
    % save back to file
    writecell(M,config_table);
    prompt = {'Is this the last mouse for today? (yes /no)'};
	dlgtitle = 'Mice Training System';
	dims = [1 45];
	definput = {'no'};
	answer = inputdlg(prompt,dlgtitle,dims,definput);
	if answer{1} == "yes"
	command = 'python path to Mice_training_data_analysis_wheel_setting.py';
	[status,cmdout] = system(command);
	disp(status);
	disp(cmdout);
	end 	
end
catch
    disp("Network down. Move manually the file after the network will be on");
end
if vr.imaging_session && ~vr.saved_imaging_session
	save_imagging_session(vr);
end
end

% each time that packet send from arduino, the values in the vr.arduino_port.UserData updates
function read_arduino_packet(src, ~)
data = readline(src);
[data_matrix  , ] = split(data,"_"); % match contain the delimiters
src.UserData.mov = str2double(data_matrix(2));
src.UserData.lick = str2double(data_matrix(3));
src.UserData.trigger = str2double(data_matrix(4));
end


% movement calculation 
function [last_wheel_spin, movement, speed, cumsum_lap_length, last_time_point] = movement_calc(vr)
cur_wheel_spin = vr.arduino_port.UserData.mov;
mov_dif = cur_wheel_spin - vr.last_wheel_spin;
if (cur_wheel_spin == 0) && (vr.last_wheel_spin > 150)  
	mov_dif = vr.p_revolution - vr.last_wheel_spin;
end 
if (cur_wheel_spin < 20) && (cur_wheel_spin > 0) && (vr.last_wheel_spin > 150)
mov_dif  = (vr.p_revolution - vr.last_wheel_spin) + (cur_wheel_spin);
end
movement = vr.r * mov_dif * (2*pi/vr.p_revolution);
cumsum_lap_length = vr.cumsum_lap_length + movement;
last_wheel_spin = cur_wheel_spin;
if vr.timeElapsed == vr.last_time_point
speed = 0;
else
speed = movement / (vr.timeElapsed - vr.last_time_point);
end
last_time_point = vr.timeElapsed;
end


% initialize the table for the data storage
function [table_path, date_path] = 	initialize_data_table()
global LOCAL_TRACKING_DIR;
columns = ["timeElapsed", "r", "encoder_val", "speed", "position", "lap_length_cumsum", "resting" ,"lick", "reward", "lap_counter", "movement", "current_World", "stage" ];
date_path = datetime(now,'ConvertFrom','datenum');
table_path_temp = datestr(date_path);
table_path_temp = strrep(table_path_temp,':','_');
table_path_temp = strrep(table_path_temp,' ','_');
table_path = strcat(table_path_temp,'.csv');
table_path = append(LOCAL_TRACKING_DIR ,table_path);
table_path = convertStringsToChars(table_path);
writematrix(columns, table_path ,'WriteMode','append');
end

% initialize the table for the data storage in the imagging session
function [table_path, date_path] = initialize_imaging_data_table()
global LOCAL_TRACKING_DIR;
columns = ["time_from_trigger", "r", "encoder_val", "speed", "position", "lap_length_cumsum", "resting" , "lick", "reward", "lap_counter", "movement", "current_World", "stage" ];
date_path = datetime(now,'ConvertFrom','datenum');
table_path_temp = datestr(date_path);
table_path_temp = strrep(table_path_temp,':','_');
table_path_temp = strrep(table_path_temp,' ','_');
table_path = strcat(table_path_temp,'.csv');
table_path = append(LOCAL_TRACKING_DIR, table_path);
table_path = convertStringsToChars(table_path);
writematrix(columns, table_path ,'WriteMode','append');
end

function save_imagging_session(vr)
% save data from training
tracking_dir = 'path to imaging_data dir \';
mouse_dir = strcat(tracking_dir, vr.cage_name,'\',vr.mouse_name);
if ~exist(mouse_dir, 'dir')
   mkdir(mouse_dir)
end
seq_file_name = 'seq_num.txt';
seq_full_path = strcat(tracking_dir, vr.cage_name,'\',vr.mouse_name, '\', seq_file_name);
seq_num = 1;
try
    seq_num = readmatrix(seq_full_path);
    seq_num = seq_num + 1;
    writematrix(seq_num, seq_full_path)
catch
    % first_time
    seq_num = 1;
    writematrix(seq_num ,seq_full_path)
end
seq_num = num2str(seq_num);
file_name = strcat(mouse_dir,'\','imaging_',seq_num, '.csv' );
try
	copyfile(vr.image_path, file_name, 'f');
catch 
	mkdir(mouse_dir);
	copyfile(vr.image_path, file_name, 'f');
end
end

function [experimentEnded, imaging_session, imaging_time] = training_or_imaging()
experimentEnded = false;
% first prompt - imaging or training
list = {'Training', 'Imaging'};
[indx,tf] = listdlg('Name','Mice Training & Imaging System','PromptString',{'Select task:'},...
    'SelectionMode','single','ListString',list,'ListSize',[150,80]);
temp = list(indx);
if tf == 0
	imaging_session = -1;
	imaging_time = 0;
    experimentEnded = true;
    stage = 'None';
    return
end
tasl = temp{1};
imaging_session = false;
if indx == 2
	imaging_session = true;
end
imaging_time = 0 ;
if imaging_session
    imaging_session = true;
    prompt = {'Imaginig duration (seconds) :',};
    dlgtitle = 'Mice Training System';
    dims = [1 45];
    definput = {'10'};
    answer_img = inputdlg(prompt,dlgtitle,dims,definput);
    imaging_time = str2double(answer_img);
end
end


function [cage_name, mouse_name, mouse_weight, save_data, training_rounds] = user_input(cage, mouse, rounds, to_save)
prompt = {'Enter cage name:','Enter mouse name:','Enter mouse weight:','Training rounds: ','Save data? (yes / no)'};
dlgtitle = 'Mice Training System';
dims = [1 45];
definput = {cage, mouse,'0', rounds, to_save};
answer = inputdlg(prompt,dlgtitle,dims,definput);
if isempty(answer)
    return;
end
cage_name = answer{1};
mouse_name = answer{2};
mouse_weight = str2double(answer{3});
training_rounds = str2num(answer{4});
save_data = false;
if answer{5} == "yes"
    save_data = true;
end
end

function [start_reward_zone, end_reward_zone] = get_reward_cords(currentWorld)
if currentWorld == 1
	start_reward_zone = 107;
	end_reward_zone = 128;
end
%if currentWorld == 2
%	start_reward_zone = ?;
%	end_reward_zone = ?;
%end

if currentWorld == 3
	start_reward_zone = 107;
	end_reward_zone = 128;
end

%if currentWorld == 4
%	start_reward_zone = ?;
%	end_reward_zone = ?;
%end

if currentWorld == 5 || currentWorld == 6 
	start_reward_zone = 0;
	end_reward_zone = 0;
end
end


function [running_time, resting_time] = timer_configurations(vr)
% measure time in seconds
if  vr.stage == "A" || vr.stage == "B"
	running_time = 4 * 60; 
	resting_time = 2 * 60;

end
if vr.stage == "C"
	running_time = 0.2 * 60;
	resting_time = 0.2 * 60;
end
if vr.stage == "D"
	running_time = 4 * 60;
	resting_time = 2 * 60;
end
if vr.stage == "E"
	running_time = 2 * 60;
	resting_time = 2 * 60;
end
if vr.stage == "F"
	running_time = 2 * 60;
	resting_time = 2 * 60;
end
end

% after each round start a new clock
function [start_resting, round_counter, start_round, resting_flag] = resting_control(vr)
start_resting = vr.start_resting;
round_counter = vr.round_counter;
start_round = vr.start_round;
resting_flag = false;
elapsed_time = toc(vr.time_elapsed_round);
if (elapsed_time >= vr.running_time) && ~vr.resting_flag
    round_counter = vr.round_counter + 1;
	start_resting = elapsed_time;
	resting_flag = true;
end
if ((elapsed_time - vr.start_resting) <  vr.resting_time) && vr.resting_flag
    resting_flag = true;
end
if ((elapsed_time - vr.start_resting) >=  vr.resting_time) && vr.resting_flag
	start_round = true;
	% in the imaging session, we will need more time between rounds, to set up the microscope
	if vr.imaging_session
		uiwait(msgbox('Ready for imaging?'));
	end
else
	start_round = false;
end
end


function [training_round_number, end_training] = check_if_training_finshed(vr)
training_round_number = vr.training_round_number;
end_training = vr.experimentEnded;
if vr.iterations == vr.lap_end_iter + 5 || vr.stage == "A" || vr.stage == "B" % true when finish rest or just finish lap in running time
	if (vr.round_counter)  >= vr.training_round_number - 1
		prompt = {'Time over - does the mouse need some more time? (yes / no)'};
		dlgtitle = 'Mice Training System';
		dims = [1 45];
		definput = {'no'};
		answer = inputdlg(prompt,dlgtitle,dims,definput);
		need_more = false;
		if answer{1} == "yes"
			need_more = true;
		end
		if need_more
			end_training = false;
			prompt = {'How many rounds?'};
			dlgtitle = 'Mice Training System';
			dims = [1 45];
			definput = {'2'};
			answer = inputdlg(prompt,dlgtitle,dims,definput);
			rounds = str2num(answer{1});
			training_round_number = vr.training_round_number + rounds;
		else
			end_training = true;
		end
	else
		end_training = false;
	end
end
end


function [got_reward, reward_counter, reward] = reward_control(vr)
cond = get_reward_condition(vr.stage, vr.position(2), vr.start_reward_zone, vr.resting_flag, vr.got_reward, vr.speed, vr.speed_limit, vr.reward_dealy, vr.reward_time, vr.timeElapsed, vr.currentWorld ,vr.black_screen);
if cond
	% give reward
	write(vr.arduino_port, vr.reward_signal, 'int64');
	% counters
	reward_counter = vr.reward_counter + 1;
	got_reward = true; % will change again in the next lap
	reward = 1;
	display("Reward = " + reward_counter);
else
	reward = 0;
	reward_counter = vr.reward_counter;
	got_reward = vr.got_reward;
end
end

function cond = get_reward_condition(stage, position, start_reward_zone, resting_flag, got_reward, speed, speed_limit, reward_dealy, reward_time, timeElapsed, currentWorld ,black_screen)
	cond = false;
    switch(stage)
		case "A"
			cond = false; %never get reward at stage A
		case "B" 
			cond1 = speed >= speed_limit; %never get reward at stage A
			cond2 = timeElapsed - reward_time  >= reward_dealy;
			cond3 = ~resting_flag;
			cond = cond1 && cond2 && cond3;
		otherwise 
			cond1 = (position >= start_reward_zone) && (~resting_flag) && (~got_reward);
            cond2 = (currentWorld ~= black_screen);
            cond = cond1 && cond2;
    end
end

function [lap_end, lap_diff] = end_of_lap_control(stage, cur_position, start_position, end_position)
% initialization of variables
lap_diff = 1;
lap_end = false;
if cur_position >= end_position
	lap_diff = 1;
	lap_end = true;
end
if cur_position <= start_position - 15
	lap_diff = -1;
	lap_end = true;
end
if stage == 'A' || stage == 'B'
    lap_end = false;
end
end


function [start_round , time_elapsed_round, first_iteration] = start_round_control(vr)
[start_round , time_elapsed_round, first_iteration] = deal(vr.start_round , vr.time_elapsed_round, vr.first_iteration);
if vr.first_iteration 
	if ~ vr.imaging_session
		disp("---------------- starting lap # " + vr.lap_counter + " ----------------");
	end
    first_iteration = false;
end
% start to measure time
if vr.start_round && ~strcmp(vr.stage, 'None') 
    t = datetime('now');
	if vr.lap_counter ~= 0 
		display("Start round " + num2str(vr.round_counter) + " at : " +  datestr(t, 'HH:MM:ss'));
		display("While session started at : " + datestr(vr.start_session_time,'HH:MM:ss'));
	end
	time_elapsed_round = tic;
	start_round = false;
end
end

% end of lap mechanism:
% 1. if training duration elapsed - finish experiment
% 2. else, check if resting time
% 3. if resting time - stop the air
% 4. if not resting - 0.5 sec of delay in black and continue 
function [got_reward, currentWorld, start_resting, round_counter, start_round, resting_flag, lap_end_flag, lap_end_iter] = end_of_round_conrol(vr)
[got_reward, currentWorld, start_resting, round_counter, ...
start_round, resting_flag, lap_end_flag, lap_end_iter] = deal(vr.got_reward, ...
vr.currentWorld, vr.start_resting, vr.round_counter, vr.start_round, vr.resting_flag, vr.lap_end_flag, vr.lap_end_iter);

if vr.lap_end && vr.lap_end_flag
	got_reward = false; % for allowed reward in the next lap
	currentWorld = vr.black_screen;
	% check if resting time - if true will turn off the air for resting time seconds
	[start_resting, round_counter, start_round, resting_flag] = resting_control(vr);
    lap_end_iter = vr.iterations;
    lap_end_flag = false;
    if resting_flag
        lap_end_flag = true;
    end
end
end

function [lap_end, lap_end_flag, currentWorld, start_reward_zone, end_reward_zone, p, dp, lap_counter, nov_env_lap_counter, cumsum_lap_length] = telaportation_control(vr)
[lap_end, lap_end_flag, currentWorld, start_reward_zone, end_reward_zone, p, dp, ...
lap_counter, nov_env_lap_counter, cumsum_lap_length] = deal(vr.lap_end, vr.lap_end_flag, vr.currentWorld, ...
vr.start_reward_zone, vr.end_reward_zone, vr.position(2), vr.dp(:), vr.lap_counter, vr.nov_env_lap_counter, vr.cumsum_lap_length);
if ~vr.resting_flag && (vr.iterations >= vr.lap_end_iter + 15) && vr.lap_end
    lap_end = false;
    lap_end_flag = true;
    currentWorld = stage_control(vr); % apply remapping here
    [start_reward_zone, end_reward_zone] = get_reward_cords(currentWorld);
	p = vr.start_position_y; % Teleport to the beginning
    dp = 0; % prevent any additional movement during lap_counteration
    lap_counter = vr.lap_counter + vr.lap_diff; % +- 1 depend if went back or forward
	if vr.lap_diff == 1
	disp("---------------- starting lap # " + lap_counter + " ----------------");
	end
	cumsum_lap_length = 0;
    if (vr.round_counter >= vr.rounds_before_novel_env)
        nov_env_lap_counter = vr.nov_env_lap_counter + vr.lap_diff; % set to zero in the last round
    end
end 
% for novel environment condition in stage F 
if ~vr.resting_flag % the air condition is for preventing changing world between trials
	nov_env_lap_counter = 0;
end
end


function [last_arduino_lick_counter, lick, lick_counter] = lick_control(vr)
	cur_lick_counter = vr.arduino_port.UserData.lick;
	if cur_lick_counter > vr.last_arduino_lick_counter
		lick = 1;
		lick_counter = vr.lick_counter + 1;
		display("Lick # " + lick_counter + " @ " + round(vr.cumsum_lap_length) /10 + " cm from the begining of the lap" 	);
	else
		lick = 0;
		lick_counter = vr.lick_counter;
	end
	last_arduino_lick_counter = cur_lick_counter;
end

function currentWorld = stage_control(vr)
	switch(vr.stage)
		case "A"
			currentWorld = vr.white_screen;
		case "B"
			currentWorld = vr.white_screen;	
		case {"C", "D", "E"}
			currentWorld = vr.basic_world;	
		case "F"
			if (vr.round_counter >= vr.rounds_before_novel_env) && (vr.nov_env_lap_counter == vr.laps_before_nov);
				currentWorld = vr.nov_env;
				t = datetime('now');
				display("Teleportation to Novel world happed at : " + datestr(t, 'HH:mm:ss'));
			else 
				currentWorld = vr.basic_world;
            end	
    end
end

function [speed_limit, last_speed_limit_change, rewards_from_last_change] = speed_limit_update(vr)
	if mod(vr.iterations,300) == 0
        display("mouse speed is: " + vr.speed);
        display("while the speed limit for reward is: " + vr.speed_limit);
    end
    last_speed_limit_change = vr.last_speed_limit_change;
    speed_limit = vr.speed_limit;
    rewards_from_last_change = vr.rewards_from_last_change;
    if (vr.timeElapsed - vr.reward_time > 30) && ((vr.timeElapsed - vr.last_speed_limit_change) > 30) && rewards_from_last_change <=3
        speed_limit = max(vr.minimum_speed_limit, vr.speed_limit - 5);
		last_speed_limit_change = vr.timeElapsed;
		rewards_from_last_change = 0;
	elseif (vr.timeElapsed - vr.reward_time < 1) && (vr.timeElapsed - vr.last_speed_limit_change) > 5 && rewards_from_last_change >=2
        speed_limit = vr.speed_limit + 5;
		last_speed_limit_change = vr.timeElapsed;
		rewards_from_last_change = 0;
    end
end

function [stage, experimentEnded] = user_input_stage()
experimentEnded = false;
list = {'A','B', 'C', 'D', 'E', 'F', 'Test water drop'};
[indx,tf] = listdlg('Name','Mice Training','PromptString',{'Select a training stage:'},...
    'SelectionMode','single','ListString',list,'ListSize',[200,150], 'InitialValue', 3);
temp = list(indx);
if tf == 0
    experimentEnded = true;
    stage = 'None';
    return
end
stage = temp{1};
if strcmp(stage,'Test water drop')
	check_drop_size();
	experimentEnded = true;
end
end

function check_drop_size()
global ARDUINO_COM_PORT;
arduino_port = serialport(ARDUINO_COM_PORT,9600);
configureTerminator(arduino_port,"CR/LF");
flush(arduino_port);
reward_counter = 0;
drip = 1;
while drip == 1 
    answer = questdlg('Press drip for check the drop size', ...
        'Drop Size Test', ...
        'drip','exit', 'drip');
    % Handle response
    switch answer
        case 'drip'
			write(arduino_port, 1 ,'int64');
            reward_counter = reward_counter + 1;
            display("Reward = " + reward_counter);
            drip = 1;
        otherwise
            drip = 0;
    end
end
end


function stage_number = get_stage_number(stage)
stage_number = 0;
if strcmp(stage, 'Test water drop') || strcmp(stage, 'None')
    stage_number = 0;
elseif stage == "A"
    stage_number = 1;
elseif stage == "B"
    stage_number = 2;
elseif stage == "C"
    stage_number = 3;
elseif stage == "D"
    stage_number = 4;
elseif stage == "E"
    stage_number = 5;
elseif stage == "F"
    stage_number = 6;
else
    ME = MException('stage number doesnt defined');
    throw(ME);
end
end


function [speed_limit, last_speed_limit_change, rewards_from_last_change, reward_time, got_reward] = stage_b_speed_control(vr)
[speed_limit, last_speed_limit_change, rewards_from_last_change, reward_time ...
,got_reward] = deal(vr.speed_limit, vr.last_speed_limit_change, ...
vr.rewards_from_last_change, vr.reward_time, vr.got_reward);
if vr.stage == "B"
	[speed_limit, last_speed_limit_change, rewards_from_last_change] = speed_limit_update(vr);
	if vr.got_reward
		reward_time = vr.timeElapsed;
		rewards_from_last_change = vr.rewards_from_last_change + 1;
        got_reward = false; 
	end
end
end

function save_iteration_data(vr)
% update table in each iteration 
if ~ vr.imaging_session
	to_update = [vr.timeElapsed, vr.r, vr.last_wheel_spin, vr.speed, vr.position(2), vr.cumsum_lap_length,  vr.resting_flag ,vr.lick, vr.reward, vr.lap_counter, vr.mouse_movement, vr.currentWorld, vr.stage_number];
	writematrix(to_update, vr.path, 'WriteMode', 'append')
else
	t = toc(vr.time_from_trigger);
	to_update = [t, vr.r, vr.last_wheel_spin, vr.speed, vr.position(2), vr.cumsum_lap_length,  vr.resting_flag, vr.lick, vr.reward, vr.lap_counter, vr.mouse_movement, vr.currentWorld, vr.stage_number];
	writematrix(to_update, vr.image_path, 'WriteMode', 'append')
end
end

function [saved_imaging_session, experimentEnded, imaging_time, trigger, time_from_trigger, imaging_session_number, currentWorld, p, dp, image_path, date_path] = imaging_control(vr)
[saved_imaging_session, experimentEnded, imaging_time, trigger, time_from_trigger, imaging_session_number, currentWorld ...
,p, dp, image_path, date_path] = deal(vr.saved_imaging_session, vr.experimentEnded, ...
vr.imaging_time, vr.trigger, vr.time_from_trigger, vr.imaging_session_number,...
vr.currentWorld, vr.position(2), vr.dp(:), vr.image_path, vr.date_path);

if vr.imaging_session && ~ vr.start_synchronization_clock
	% wait untill trigger the inagging session fron ThorImage
    answer = questdlg('Press O.K to start to wait for a trigger. Make sure the trigger is turned off before.', ...
    'imaging_session', ...
    'O.k', 'exit', 'O.k');
    % Handle response
    saved_imaging_session = false; % prevent double saving
    switch answer
        case 'exit'
            saved_imaging_session = true; % prevent double saving
            experimentEnded = true;
    end
    if  ~strcmp(answer, 'exit')
    if ~ vr.first_iteration
    prompt = {'Imaging duration (seconds) :',};
    dlgtitle = 'Mice Training System';
    dims = [1 45];
    definput = {num2str(vr.imaging_time)};
    answer_img = inputdlg(prompt,dlgtitle,dims,definput);
    imaging_time = str2double(answer_img);  
	%[wheel_spin_counter, lick_counter, trigger] = parse_arduino_data(vr);
	%while (strcmp(trigger,'0')) && (~ vr.experimentEnded)
	%	[wheel_spin_counter, lick_counter, trigger] = parse_arduino_data(vr);
    %end
	trigger = vr.arduino_port.UserData.trigger;
	while (trigger == 0) && (~ vr.experimentEnded)
		trigger = vr.arduino_port.UserData.trigger;
    end
    end
	time_from_trigger = tic;
	imaging_session_number = vr.imaging_session_number + 1;
	start_synchronization_clock = true;
	currentWorld = vr.basic_world;
    p = vr.start_position_y; % Teleport to the beginning
    dp = 0; % prevent any additional movement during lap_counteration
	[image_path, date_path] = initialize_imaging_data_table();
end
end
end

function [start_synchronization_clock, currentWorld, saved_imaging_session, start_round] =  end_imaging_session(vr)
[start_synchronization_clock, currentWorld, saved_imaging_session, start_round] ...
= deal(vr.start_synchronization_clock, vr.currentWorld, vr.saved_imaging_session, vr.start_round);

if (vr.imaging_session && toc(vr.time_from_trigger) >= vr.imaging_time) 
	vr.start_synchronization_clock = false;
	vr.currentWorld = vr.black_screen;
	save_imagging_session(vr);
    vr.saved_imaging_session = true;
    vr.start_round = true; % for the next omagging session. thus, the resing contol mechanisem will work
end
end   