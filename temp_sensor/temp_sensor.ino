
#include "DHT.h"
#include <stdlib.h>
#include <SerialCmd.h>

#define DHTPIN 2 
#define DHTTYPE DHT22  
DHT dht(DHTPIN, DHTTYPE);
float temp;
float hum;

SerialCmd mySerCmd( Serial );


void read_sensor(void){
  temp = dht.readTemperature();

  hum = dht.readHumidity();
  if (isnan(hum) || isnan(temp) ) {
    return;}
  mySerCmd.Print(String(temp)+','+String(hum)+"\r\n");
}



void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);
  dht.begin();
  mySerCmd.AddCmd ( "READ", SERIALCMD_FROMALL, read_sensor );

}

void loop() {
  int8_t ret;
  ret = mySerCmd.ReadSer();
  if ( ret == 0 ) {
      mySerCmd.Print ( ( char * ) "ERROR: Urecognized command. \r\n" );
  }
}
