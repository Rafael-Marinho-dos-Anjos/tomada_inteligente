#include "driver/timer.h"
#include "SPIFFS.h"
#include <WiFi.h>
#include <HTTPClient.h>


// Definição do timer
#define TIMER_GROUP TIMER_GROUP_0
#define TIMER_NUMBER TIMER_0

// Constantes do sistema
const int config_pin = 4; // Botão para ativar modo de configuração
const int tens_pin = 5; // Pino de leitura da tensão
const int curr_pin = 6; // Pino de leitura da corrente
const int cap_pins[] = {18, 19, 20, 21, 22, 23, 15, 17}; // Pinos de chaveamento do banco de capacitores
bool cap_switch[] = {false, false, false, false, false, false, false, false};

const int send_data_period = 3; // Período entre dois envios de dados seguidos em segundos
const String server_url = "http://10.0.0.222:5000/"; // Endereço do servidor da aplicação web

const int samp_freq = 1000; // Frequência de amostragem
const int samp_period = 1000000 / samp_freq; // Período da amostragem

const float rel_transf_tens = 160.0; // Relação transformação da tensão lida
const float rel_transf_curr = 10.0; // Relação transformação da corrente lida

const float cap_base = 0.00000056; // Capacitância base
const String cap_str = "560e-9"; // String valor capacitância base
const int cap_num = 8; // Número de capacitores

const float pi = 3.14159265359;

// Variaveis
int tens_per_count = 0; // Contagem do periodo da tensao
int curr_per_count = 0; // Contagem do periodo da corrente
int phase_count = 0; // Contagem do periodo da defasagem

bool is_reading_tens = true; // Flag de leitura da tensão
bool is_reading_curr = false; // Flag de leitura da corrente
bool counting_tens = false; // Flag de leitura da tensão
bool counting_curr = false; // Flag de leitura da corrente

float tens_acc = 0; // Acumulador tensão
float curr_acc = 0; // Acumulador corrente
float tens_rms = 0; // Tensão RMS
float curr_rms = 0; // Corrente RMS

float frequence = 0; // Frequência da tensão lida
float phase = 0; // Defasagem em radianos
float fp = 0; // Fator de potência

float s = 0; // Potência aparente
float p = 0; // Potência ativa
float q = 0; // Potência reativa

int tens_read; // Leitura atual da tensao
int curr_read; // Leitura atual da corrente

float current_tens; // Leitura atual da tensao convertida
float current_curr; // Leitura atual da corrente convertida

float last_tens = 0; // Leitura anterior da tensao
float last_curr = 0; // Leitura anterior da corrente

int cap_count = 0; // Contador para atualização do banco
float cap_acc = 0; // Acumulador da capacitância

// Acumuladores de leitura
float meanS = 0;
float meanV = 0;
float meanFp = 0;
float meanFreq = 0;

// Variaveis de configuração do usuário
String ssid = "Casa06";
String wifi_password = "1q2w3e4r";
String username = "";
String device_code = "ABCD";

bool config_loaded = false;


void save_config(String wifi_ssid, String wifi_psswrd, String usrnm, String dvc_cd) {
  File file = SPIFFS.open("/config.txt", FILE_WRITE);

  if (!file) {
    file.close();
    return;
  }

  if (!file.print(wifi_ssid + "\n")) { return; }
  if (!file.print(wifi_psswrd + "\n")) { return; }
  if (!file.print(usrnm + "\n")) { return; }
  if (!file.print(dvc_cd + "\n")) { return; }

  file.close();
}

void load_config() {
  File file = SPIFFS.open("/config.txt", FILE_READ);

  if (!file) {
    file.close();
    return;
  }

  String content;
  while (file.available()) {
    content = file.readStringUntil('\n');

    if (username != "") {
      device_code = content;
    }
    else if (wifi_password != "") {
      username = content;
    }
    else if (ssid != "") {
      wifi_password = content;
    }
    else {
      ssid = content;
    }
  }

  file.close();
  config_loaded = true;
}

void config_wifi() {
  char* ssid     = "config_tomada";
  char* password = "12345678";

  WiFiServer server(80);

  String header;

  // IP do serviço de configuração 192.168.1.184
  IPAddress local_IP(192, 168, 1, 184);
  IPAddress gateway(192, 168, 1, 1);
  IPAddress subnet(255, 255, 0, 0);
  IPAddress primaryDNS(8, 8, 8, 8);
  IPAddress secondaryDNS(8, 8, 4, 4);

  if (!WiFi.config(local_IP, gateway, subnet, primaryDNS, secondaryDNS)) {
    server.stop();
    server.close();
    return;
  }

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }

  while (!config_loaded) {
    WiFiClient client = server.available();
  
    // TODO -> Página de configuração

  }
  
  server.stop();
  server.close();
}

float conversion(int val, float rel) {
  float pin_tension = val * 3.3 / 4096;
  pin_tension -= 1.65;

  return pin_tension * rel;
}

void power() {
  s = tens_rms * curr_rms;
  p = s * fp;
  q = s * sin(phase);
}

void cap_bank_update() {
  if (frequence == 0) {
    return;
  }
  float capacitance = q / (2 * pi * frequence * pow(tens_rms, 2));

  cap_acc += capacitance;
  cap_count += 1;

  if (cap_count < 50) {
    return;
  }

  capacitance = cap_acc / cap_count;
  cap_acc = 0;
  cap_count = 0;
  
  //Serial.print("q: ");
  //Serial.print(q);
  //Serial.print("  freq: ");
  //Serial.print(frequence);
  //Serial.print("  v: ");
  //Serial.print(tens_rms);
  //Serial.print("  cap_tot: ");
  //Serial.print(capacitance*1000000000);
  int switching = capacitance / cap_base;
  int val = pow(2, cap_num);
  //Serial.print("nF  switch: ");
  //Serial.print(switching);
  //Serial.print("  val: ");
  //Serial.println(val);

  for (int i = cap_num - 1; i >= 0; i--) {
    val = val / 2;
    if (switching >= val) {
      digitalWrite(cap_pins[i], HIGH);
      cap_switch[i] = true;
      //Serial.print("1");
      switching -= val;
    }
    else {
      digitalWrite(cap_pins[i], LOW);
      cap_switch[i] = false;
      //Serial.print("0");
    }
  }
  //Serial.println();
}

void reading() {
  // Leitura da tensão e da corrente
  tens_read = analogRead(tens_pin);
  curr_read = analogRead(curr_pin);

  // Conversão da leitura
  tens_read = conversion(tens_read, rel_transf_tens);
  curr_read = conversion(curr_read, rel_transf_curr);

  // Acumuladores
  if (counting_tens) {
    tens_per_count++;
    tens_acc += sq(tens_read);
  }
  if (counting_curr) {
    curr_per_count++;
    curr_acc += sq(curr_read);
  }
  phase_count++;
}

void zero_passage() {
  // Passagem por zero
  if (tens_read >= 0 and last_tens < 0) {
    phase_count = 0;
    if (is_reading_tens && counting_tens) {
      frequence = samp_freq / tens_per_count;
      tens_rms = sqrt(tens_acc / tens_per_count);
  
      tens_acc = 0;
      tens_per_count = 0;

      is_reading_tens = false;
      counting_tens = false;
      is_reading_curr = true;
    }
    if (is_reading_tens && !counting_tens) {
      counting_tens = true;
    }
  }
  
  // Passagem por zero
  if (curr_read >= 0 and last_curr < 0) {
    phase = 2 * pi * phase_count * frequence / samp_freq;
    fp = cos(phase);
    if (is_reading_curr && counting_curr) {
      curr_rms = sqrt(curr_acc / curr_per_count);
  
      curr_acc = 0;
      curr_per_count = 0;
      power();
      cap_bank_update();

      is_reading_curr = false;
      counting_curr = false;
      is_reading_tens = true;
    }
    if (is_reading_curr && !counting_curr) {
      counting_curr = true;
    }
  }

  last_tens = tens_read;
  last_curr = curr_read;
}

//void IRAM_ATTR onTimer(void *params) {
void leitura() {
    reading();
    zero_passage();
}

void postMeasure(float sMean, float fpMean, float freqMean, float vMean) {
  if(WiFi.status()== WL_CONNECTED){
    WiFiClient client;
    HTTPClient http;

    Serial.println("POST:");
  
    // Your Domain name with URL path or IP address with path
    http.begin(client, server_url + "send_measure/" + device_code + "/");
    Serial.println(server_url + "send_measure/" + device_code + "/");
    
    // If you need Node-RED/server authentication, insert user and password below
    //http.setAuthorization("REPLACE_WITH_SERVER_USERNAME", "REPLACE_WITH_SERVER_PASSWORD");
    
    // Specify content-type header
    http.addHeader("Content-Type", "application/x-www-form-urlencoded");
    // Data to send with HTTP POST
    String httpRequestData = "device_code=";
    httpRequestData += device_code;
    httpRequestData += "&s=";
    httpRequestData += String(sMean);
    httpRequestData += "&v=";
    httpRequestData += String(vMean);
    httpRequestData += "&fp=";
    httpRequestData += String(fpMean);
    httpRequestData += "&freq=";
    httpRequestData += String(freqMean);
    httpRequestData += "&cap_base=";
    httpRequestData += cap_str;
    httpRequestData += "&cap_switch=";
    for (int i = cap_num - 1; i >= 0; i--) {
      if (cap_switch[i]) {
        httpRequestData += "1";
      }
      else {
        httpRequestData += "0";
      }
    }

    Serial.println(httpRequestData);

    // Send HTTP POST request
    int httpResponseCode = http.POST(httpRequestData);
    
    // If you need an HTTP request with a content type: application/json, use the following:
    //http.addHeader("Content-Type", "application/json");
    //int httpResponseCode = http.POST("{\"api_key\":\"tPmAT5Ab3j7F9\",\"sensor\":\"BME280\",\"value1\":\"24.25\",\"value2\":\"49.54\",\"value3\":\"1005.14\"}");

    http.end();
  }
}

void setup() {
    // Configurando pinos de entrada e saída
    pinMode(tens_pin, INPUT);
    pinMode(curr_pin, INPUT);
    pinMode(config_pin, INPUT);

    for (int i = 0; i < cap_num; i++) {
      pinMode(cap_pins[i], OUTPUT);
    }

    // if (digitalRead(config_pin) == HIGH) {
    //   config_wifi();
    // }
    // else {
    //   load_config();
    // }
    
    // Iniciando o timer
    timer_config_t config;
    // config.divider = 80;                      // Divisor do clock
    // config.counter_dir = TIMER_COUNT_UP;      // Contagem crescente
    // config.counter_en = TIMER_PAUSE;          // Inicia pausado
    // config.alarm_en = TIMER_ALARM_EN;         // Habilita alarme
    // config.auto_reload = TIMER_AUTORELOAD_EN; // Recarregar automaticamente

    // timer_init(TIMER_GROUP, TIMER_NUMBER, &config);

    // // Configuração do timer
    // timer_set_alarm_value(TIMER_GROUP, TIMER_NUMBER, samp_period);
    // timer_enable_intr(TIMER_GROUP, TIMER_NUMBER);
    // timer_isr_register(TIMER_GROUP, TIMER_NUMBER, onTimer, NULL, ESP_INTR_FLAG_IRAM, NULL);

    // // Inicia o timer
    // timer_start(TIMER_GROUP, TIMER_NUMBER);

    Serial.begin(9600);

    WiFi.begin(ssid, wifi_password);

    while (WiFi.status() != WL_CONNECTED) {
      delay(500);
      Serial.print(".");
    }
}

void loop() {
    for (int i = 0; i < send_data_period; i++) {
      for (int j = 0; j < samp_freq; j++) {
        unsigned long elapsed_time = micros();
        leitura();
        elapsed_time = micros() - elapsed_time;
        //Serial.print(elapsed_time);
        //Serial.print(" ");
        //Serial.println(samp_period);
        if (elapsed_time < samp_period){
          delayMicroseconds(samp_period - elapsed_time);
        }
      }
      meanV += tens_rms;
      meanS += s;
      meanFp += fp;
      meanFreq += frequence;
    }

    meanV = meanV / send_data_period;
    meanS = meanS / send_data_period;
    meanFp = meanFp / send_data_period;
    meanFreq = meanFreq / send_data_period;

    postMeasure(meanS, meanFp, meanFreq, meanV);

    meanV = 0;
    meanS = 0;
    meanFp = 0;
    meanFreq = 0;
}
