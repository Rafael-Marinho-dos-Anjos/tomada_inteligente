#include "driver/timer.h"
#include "SPIFFS.h"
#include <WiFi.h>

// Bluetooth é muito pesado pra utilizar junto :'(
// #include <BLEDevice.h>
// #include <BLEServer.h>

// #define SERVICE_UUID        "ec8020a2-6317-4166-90c3-d52a7d904027"
// #define CHARACTERISTIC_UUID "f6350992-dd73-4afe-b170-2961b66c75d7"

// Definição do timer
#define TIMER_GROUP TIMER_GROUP_0
#define TIMER_NUMBER TIMER_0

// Constantes do sistema
const int config_pin = 36; // Botão para ativar modo de configuração
const int tens_pin = 34; // Pino de leitura da tensão
const int curr_pin = 35; // Pino de leitura da corrente
const int cap_pins[] = {21, 22, 23, 25, 26, 27, 32, 33}; // Pinos de chaveamento do banco de capacitores

const String device_name = "BT - Tomada Inteligente"; // Nome do dispositivo a ser mostrado no Bluetooth

const int send_data_period = 300; // Período entre dois envios de dados seguidos em segundos
const String server_url = ""; // Endereço do servidor da aplicação web

const int samp_freq = 3000; // Frequência de amostragem
const int samp_period = 1000000 / samp_freq; // Período da amostragem

const float rel_transf_tens = 1.0; // Relação transformação da tensão lida
const float rel_transf_curr = 1.0; // Relação transformação da corrente lida

const float cap_base = 0.000000011; // Capacitância base
const int cap_num = 8; // Número de capacitores

const float pi = 3.14159265359;

// Variaveis
int tens_per_count = 0; // Contagem do periodo da tensao
int curr_per_count = 0; // Contagem do periodo da corrente
int phase_count = 0; // Contagem do periodo da defasagem

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

// Variaveis de configuração do usuário
String ssid = "";
String wifi_password = "";
String username = "";
String device_code = "";

bool config_loaded = false;

// Bluetooth
// BLEServer* pServer = NULL;
// BLECharacteristic* pCharacteristic = NULL;

// class CharacteristicCallBack: public BLECharacteristicCallbacks {
//   void onWrite(BLECharacteristic *pChar) override { 
//     String config_string = pChar->getValue();

//     // TODO -> Leitura dos valores
    
//     config_loaded = true;
//   }
// };

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
  float pin_tension = val * 1.65 / 4096;
  pin_tension -= 1.65;

  return pin_tension * rel;
}

void power() {
  s = tens_rms * curr_rms;
  p = s * fp;
  q = s * sin(phase);
}

void cap_bank_update() {
  float capacitance = q / (2 * pi * frequence * tens_rms);
  int switching = capacitance / cap_base;
  int val = pow(2, cap_num);

  for (int i = cap_num - 1; i >= 0; i--) {
    val = val / 2;
    if (switching >= val) {
      digitalWrite(cap_pins[i], HIGH);
      switching -= val;
    }
    else {
      digitalWrite(cap_pins[i], LOW);
    }
  }
}

void reading() {
  // Leitura da tensão e da corrente
  tens_read = analogRead(tens_pin);
  curr_read = analogRead(curr_pin);

  tens_per_count++;
  curr_per_count++;
  phase_count++;

  // Conversão da leitura
  tens_read = conversion(tens_read, rel_transf_tens);
  curr_read = conversion(curr_read, rel_transf_curr);

  // Acumuladores
  tens_acc += sq(tens_read);
  curr_acc += sq(curr_read);
}

void zero_passage() {
  // Passagem por zero
  if (tens_read >= 0 and last_tens < 0) {
    frequence = samp_freq / tens_per_count;
    tens_rms = sqrt(tens_acc / tens_per_count);

    tens_acc = 0;
    tens_per_count = 0;
    phase_count = 0;
  }
  
  // Passagem por zero
  if (curr_read >= 0 and last_curr < 0) {
    curr_rms = sqrt(curr_acc / curr_per_count);

    phase = 2 * pi * phase_count * frequence / samp_freq;
    fp = cos(phase);

    curr_acc = 0;
    curr_per_count = 0;
    power();
    cap_bank_update();
  }

  last_tens = tens_read;
  last_curr = curr_read;
}

void IRAM_ATTR onTimer(void *params) {
    reading();
    zero_passage();
}

void setup() {
    // Configurando pinos de entrada e saída
    pinMode(tens_pin, INPUT);
    pinMode(curr_pin, INPUT);
    pinMode(config_pin, INPUT);

    for (int i = 0; i < cap_num; i++) {
      pinMode(cap_pins[i], OUTPUT);
    }

    if (digitalRead(config_pin == HIGH)) {
      config_wifi();

//       BLEDevice::init(device_name);
//       pServer = BLEDevice::createServer();
//       BLEService *pService = pServer->createService(SERVICE_UUID);
//       
//       pCharacteristic = pService->createCharacteristic(
//                       CHARACTERISTIC_UUID,
//                       BLECharacteristic::PROPERTY_READ   |
//                       BLECharacteristic::PROPERTY_WRITE 
//                     );         
//   
//       pCharacteristic->setCallbacks(new CharacteristicCallBack());
//       pService->start();
//       
//       while(!config_loaded) {
//         delay(100);
//       }
    }
    else {
      load_config();
    }
    
    // Iniciando o timer
    timer_config_t config;
    config.divider = 80;                      // Divisor do clock
    config.counter_dir = TIMER_COUNT_UP;      // Contagem crescente
    config.counter_en = TIMER_PAUSE;          // Inicia pausado
    config.alarm_en = TIMER_ALARM_EN;         // Habilita alarme
    config.auto_reload = TIMER_AUTORELOAD_EN; // Recarregar automaticamente

    timer_init(TIMER_GROUP, TIMER_NUMBER, &config);

    // Configuração do timer
    timer_set_alarm_value(TIMER_GROUP, TIMER_NUMBER, samp_period);
    timer_enable_intr(TIMER_GROUP, TIMER_NUMBER);
    timer_isr_register(TIMER_GROUP, TIMER_NUMBER, onTimer, NULL, ESP_INTR_FLAG_IRAM, NULL);

    // Inicia o timer
    timer_start(TIMER_GROUP, TIMER_NUMBER);
}

void loop() {
    // Não faz nada
}
