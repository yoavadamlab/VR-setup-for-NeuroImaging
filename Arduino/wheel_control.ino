// pin numbers
int reward_pin = 5; // pin connected to the reward valve
int lick_pin = 4;
int trigger_pin = 6; // imaging trigger from ThorImage DAQ
// signals values from virmen
int virmen_signal = 0; // signal from virmen, initialize to 0. 0 mean that no signal was send
int REWARD_SIGNAL = 1; // signal from virmen that a new session started
int START_SIGNAL = 2; // signal from virmen that a new session started
int END_SIGNAL = 3; // signal from virmen that a new session started
// variables
int last_lick_state = 0;
int lick_counter = 0;   
int reward_duration = 40;
int imaging_trigger = 0;
unsigned long last_send = 0;
int send_interval = 10; // send data to virmen each 10 ms
bool finish_session = false ;
// variables for movement detection
int encoder_A = 2; //connected to digital 2, black
int encoder_B = 3; //connected to digital 3, white
volatile long last_counter, movement_counter = 0; //This variable will increase or decrease depending on the rotation of encoder
const int p_revolutions = 400; // number of pulses per revolution
 // variables for ThosSync TTL (which needed to validate merging Imaging and Behavior)
int ttl_duration = 10;
int TTL_SIGNAL = 4; // signal from virmen that a record just saved to csv
int reward_ttl_pin = 7;
int LAP_END_SIGNAL = 5;
// variables for lick ttl
bool lick_report_to_TS = false;
int lick_ttl_pin = 8;
unsigned long lick_report_start_time = 0;
int lick_ttl_duration = 10;

void setup() {
  pinMode(trigger_pin, INPUT);
  pinMode(reward_pin, OUTPUT);
  pinMode(lick_pin, INPUT);
  pinMode(reward_ttl_pin, OUTPUT);
  pinMode(lick_ttl_pin, OUTPUT);
  // interupt pins
  pinMode(encoder_A, INPUT_PULLUP); // internal pullup input pin 2
  pinMode(encoder_B, INPUT_PULLUP); // internal pullup input pin 3
  attachInterrupt(digitalPinToInterrupt(encoder_A), a_rise, RISING); //A rising pulse from encodenren activated ai0()
  attachInterrupt(digitalPinToInterrupt(encoder_B), b_rise, RISING); //B rising pulse from encodenren activated ai1()
  Serial.begin(38400);
  while (!Serial) delay(1);
  //while (Serial.available()) Serial.read(); // this line is for flushing the serial. we didn't need it, but keep it here just in case 
}


void loop() {
  virmen_signal = read_virmen_signal();
  start_session();
  imaging_trigger = digitalRead(trigger_pin);
  reward_control();
  lick_control();
  send_data_to_virmen();
}

int read_virmen_signal() {
  int val = 0; // if nothing was send from virmen set to 0
  if (Serial.available() > 0)  // if data in the reader buffer
  {
     val = Serial.read();
    }
  return val;
}

void start_session() {
   if (virmen_signal == START_SIGNAL)
    {
    lick_counter = 0;
    movement_counter = 0;
    finish_session = false;
    }
}

void end_session() {
   if (virmen_signal == END_SIGNAL)
    {
    finish_session = true;
    }
}

void lick_control(){
  int lick = digitalRead(lick_pin);
  if (last_lick_state != lick)
  {
    lick_counter += lick;
    send_lick_ttl_to_TS();
  }
  last_lick_state = lick;
  if ((lick_report_to_TS == true) && ((millis() - lick_report_start_time) >= lick_ttl_duration))
  {
    digitalWrite(lick_ttl_pin, LOW);
    lick_report_to_TS = false;
  }
  }

void send_lick_ttl_to_TS(){
  if ((lick_report_to_TS == false) && (last_lick_state ==0))
  {  
    digitalWrite(lick_ttl_pin, HIGH);
    lick_report_to_TS = true;
    lick_report_start_time = millis();
  }
}
void reward_control() {
   if (virmen_signal == REWARD_SIGNAL)
      {
      digitalWrite(reward_pin, HIGH);
      digitalWrite(reward_ttl_pin, HIGH);
      unsigned long start = millis();
      while ((millis() - start) < reward_duration)  {  
        }   
      digitalWrite(reward_pin, LOW); 
      digitalWrite(reward_ttl_pin, LOW);  
        }
}
 
void send_data_to_virmen() {
  unsigned long t = millis();
  if ((t - last_send) > send_interval) 
  {
    last_send = t;
    Serial.print("_");
    Serial.print(movement_counter);
    Serial.print("_");
    Serial.print(lick_counter);
    Serial.print("_");
    Serial.print(imaging_trigger);
    Serial.println("_");
   }
  
}

// movement methods

  // activated if encoder_A is going from LOW to HIGH
  // Check encoder_B to determine the direction
  void a_rise() 
  {
  if(digitalRead(encoder_B)==LOW) 
    { movement_counter++;}
  else 
    { movement_counter--;}
  check_if_end_revolution();
  }

  //  activated if encoder_B is going from LOW to HIGH
  // Check encoder_A to determine the direction
  void b_rise() 
  {
  if(digitalRead(encoder_A)==LOW) 
    { movement_counter--;}
  else 
    { movement_counter++;}
  check_if_end_revolution();
  }

  void check_if_end_revolution()
  {
    if (movement_counter == p_revolutions)
    {movement_counter = 0;}
  }
