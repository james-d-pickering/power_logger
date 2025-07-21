import serial
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets
from PyQt6 import QtCore, QtWidgets, QtGui
from PyQt6.QtWidgets import ( QApplication, QPushButton, QLabel, QMainWindow, 
                        QVBoxLayout, QWidget, QTextEdit, QLineEdit, QGridLayout,
                        QHBoxLayout, QComboBox, QCheckBox, QMessageBox)  
from PyQt6.QtCore import pyqtSignal, pyqtSlot, QTimer
from datetime import datetime
import numpy as np
import os
from time import sleep



class PowerLoggerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.update_time_mins = 5
        self.setWindowTitle("LCUBS Power Logger")
        self.resize(1600, 900)
        self.previous_log = False #check if a previous log file exists so we don't mess up plots
        self.arduino = serial.Serial(
            port='COM6',
            baudrate=9600,
            timeout=5,
        )

        self.ser = serial.Serial(
            port='COM4',  # Adjust this to your serial port
            baudrate=19200,        # Adjust the baud rate as needed
            timeout=5,            # Timeout for read operations
            stopbits=serial.STOPBITS_ONE,  # Number of stop bits
            bytesize=serial.EIGHTBITS,      # Number of data bits
        )

        # Create a central widget

        label_widgets = []
        self.ntraces = 10
 # Default update time in minutes
        label_layout = QGridLayout()
        # Add widgets
        self.status_label = QLabel("Status: Not connected")
        self.arduino_status_label = QLabel("Arduino Status: Not connected")
        label_widgets.append(self.arduino_status_label)
        label_widgets.append(self.status_label) 
        self.power_label = QLabel("Power: N/A")
        label_widgets.append(self.power_label)
        self.wavelength_label = QLabel("Wavelength: N/A")
        label_widgets.append(self.wavelength_label)
        self.humidity_label = QLabel("Internal Humidity: N/A")
        label_widgets.append(self.humidity_label)
        self.shutter_label = QLabel("Shutter: N/A")
        label_widgets.append(self.shutter_label)
        self.laser_status_label = QLabel("Laser Status: N/A")
        label_widgets.append(self.laser_status_label)
        self.modelocked_label = QLabel("Modelocked: N/A")
        label_widgets.append(self.modelocked_label)

        self.room_temp_label = QLabel("Room Temperature: N/A")
        label_widgets.append(self.room_temp_label)
        self.room_humidity_label = QLabel("Room Humidity: N/A")
        label_widgets.append(self.room_humidity_label)

        self.diode1_temp_label = QLabel("Diode 1 Temp: N/A")
        label_widgets.append(self.diode1_temp_label)
        self.diode2_temp_label = QLabel("Diode 2 Temp: N/A")
        label_widgets.append(self.diode2_temp_label)
        self.diode1_heatsink_temp_label = QLabel("Diode 1 Heatsink Temp: N/A")
        label_widgets.append(self.diode1_heatsink_temp_label)
        self.diode2_heatsink_temp_label = QLabel("Diode 2 Heatsink Temp: N/A")
        label_widgets.append(self.diode2_heatsink_temp_label)
        self.baseplate_temp_label = QLabel("Baseplate Temp: N/A")
        label_widgets.append(self.baseplate_temp_label)
        self.diode1_current_label = QLabel("Diode 1 Current: N/A")
        label_widgets.append(self.diode1_current_label)
        self.diode2_current_label = QLabel("Diode 2 Current: N/A")
        label_widgets.append(self.diode2_current_label)
        self.lbo_temp_label = QLabel("LBO Temp: N/A")
        label_widgets.append(self.lbo_temp_label)
        self.etalon_temp_label = QLabel("Etalon Temp: N/A")
        label_widgets.append(self.etalon_temp_label)
    
        self.set_temps_title = QLabel("Temperature Setpoints:")
        label_widgets.append(self.set_temps_title)
        self.set_temps_title.setStyleSheet("font-weight: bold")
        self.set_temps_label = QLabel("Set Temperatures: N/A")
        label_widgets.append(self.set_temps_label)
        
        self.update_time_box = QLabel('Updates every '+str(self.update_time_mins)+' minutes')
        label_widgets.append(self.update_time_box)

        self.close_shutter_button = QPushButton("Close Shutter")
        label_widgets.append(self.close_shutter_button) 

        self.open_shutter_button = QPushButton("Open Shutter")
        label_widgets.append(self.open_shutter_button)

        self.update_time = int(float(self.update_time_mins) * 60 * 1000)  # Convert minutes to milliseconds

        hwidth = 50
        i = 0; j = 0
        for widget in label_widgets:
            label_layout.addWidget(widget, i, j)
            i += 1
            if i % hwidth == 0:
                i = 0
                j += 1

        self.data = []
        self.timestamps = []
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Create a layout
        self.layout = QGridLayout()

        self.room_temp_humidity_plot = pg.PlotWidget(title="Room Temperature and Humidity", labels={'left':'Temperature (°C) or Humidity (%)', 'bottom': 'Time'})

        self.room_temp_humidity_plot.addLegend(brush='darkgray', labelTextColor='black', offset=(0, 20))
        self.temp_current_plots = pg.PlotWidget(title="Laser Temperatures and Currents", labels={'left': 'Temperature (°C) or Current (mA)', 'bottom': 'Time'})
        self.temp_current_plots.addLegend(brush='darkgray', labelTextColor='black', offset=(0, 20))
        self.plot = pg.PlotWidget(title="Chameleon Output Power Over Time", labels={'left': 'Power (mW)', 'bottom': 'Time'})
        axis = pg.DateAxisItem(orientation='bottom')
        self.plot.setAxisItems({'bottom': axis})

        self.layout.addWidget(self.plot, 0, 0)
        self.layout.addWidget(self.temp_current_plots, 2, 0)
        self.layout.addWidget(self.room_temp_humidity_plot, 1, 0)
        self.central_widget.setLayout(self.layout)
        self.layout.addLayout(label_layout, 0, 1, 3, 1)  # Add the label layout to the right of the plots
        self.array_length = 10000

        if os.path.exists('power_log.txt'):
            print("Found previous log file, loading data...")
            self.previous_log = True
            with open('power_log.txt', 'r') as f:
                lines = f.readlines()

                self.data = [[] for _ in range(self.ntraces)]
                self.room_data = [[], []]
                self.timestamps = []    
                for idx, line in enumerate(lines):
                    if idx == 0:  # Skip the header line
                        continue 
                    data = line.strip().split(',')

                    self.timestamps.append(datetime.fromisoformat(data[0]))

                    for i in range(self.ntraces):
                        self.data[i].append(float(data[i+1]))

                    self.room_data[0].append(float(data[-2]))
                    self.room_data[1].append(float(data[-1]))
   
                
        else:
            print("No previous log file found, starting fresh.")
            with open('power_log.txt', 'w') as f:
                f.write("Timestamp,Power,Baseplate Temp,Diode 1 Temp,Diode 2 Temp,Diode 1 Heatsink Temp,Diode 2 Heatsink Temp,LBO Temp,Etalon Temp,Diode 1 Current,Diode 2 Current,Room Temperature,Room Humidity\n")
            
            self.array_length = 10000
            self.temp_current_data = [[] for _ in range(self.ntraces-1)]
            self.room_data = [[], []]
            self.data = [[0] for trace in range(self.ntraces)]  # Initialize data for each trace
                                
                # power, baseplate temp diode1 temp, diode 2 temp, diode 1 heatsink temp, diode 2 heatsink temp, lbo temp, etalon temp, diode 1 current, diode 2 current
            self.timestamps = [ datetime.now() for x in self.data[0]]  # Timestamps for the x-axis
            
        self.power_trace = self.plot.plot(x=[x.timestamp() for x in self.timestamps], y=self.data[0],
                         pen='y')

        self.temp_current_traces = []
        self.temp_current_trace_names = ['Baseplate Temp', 'Diode 1 Temp', 'Diode 2 Temp', 'Diode 1 Heatsink Temp',
                                         'Diode 2 Heatsink Temp', 'LBO Temp', 'Etalon Temp', 
                                         'Diode 1 Current', 'Diode 2 Current']

        self.room_data_traces = []  
        self.room_data_trace_names = ['Room Temperature', 'Room Humidity']
   
        for idx, item in enumerate(self.data[1:]):
            self.temp_current_traces.append(self.temp_current_plots.plot(x=[x.timestamp() for x in self.timestamps], 
                                        y=self.data[idx+1], pen=pg.intColor(idx, hues=len(self.data)), name=self.temp_current_trace_names[idx]))

        for idx, item in enumerate(self.room_data):
            self.room_data_traces.append(self.room_temp_humidity_plot.plot(x=[x.timestamp() for x in self.timestamps], 
                                        y=self.room_data[idx], pen=pg.intColor(idx, hues=len(self.room_data)), name=self.room_data_trace_names[idx]))
       


        self.open_serial_connection_laser()



        self.open_serial_connection_arduino()

        self.start_logging()




    def open_serial_connection_arduino(self):
        try:
            if not self.arduino.is_open:
                self.arduino.open()
            self.arduino_status_label.setText("Status: Connected to Arduino on " + self.arduino.name)
            sleep(2) #need to wait for the arduino here
            self.room_temp, self.room_humidity = self.query_arduino_sensor()
            if not self.previous_log:
                self.room_data[0].append(float(self.room_temp))
                self.room_data[1].append(float(self.room_humidity))
            self.room_temp_label.setText(f"Room Temperature: {self.room_temp} °C")
            self.room_humidity_label.setText(f"Room Humidity: {self.room_humidity} %")
            self.arduino_connected = True

        except serial.SerialException as e:
            QMessageBox.critical(self, "Connection Error", str(e))
            self.arduino_status_label.setText("Status: Not connected")


    def open_serial_connection_laser(self):
        try:
            if not self.ser.is_open:
                self.ser.open()
            self.status_label.setText("Status: Connected to laser on " + self.ser.name)
            shutter_status = self.query_shutter()
            laser_status = self.query_laser_on()
            power_status = self.query_power()
            wavelength_status = self.query_wavelength()
            humidity_status = self.query_humidity()
            modelocked_status = self.query_modelocked()
            self.set_temps = self.query_set_temperatures() #diode1, diode2, lbo, etalon set temperatures
            self.diode1_temp, self.diode2_temp = self.query_diode_temperature()
            self.diode1_heatsink_temp, self.diode2_heatsink_temp = self.query_diode_heatsink_temperature()
            self.baseplate_temp = self.query_baseplate_temperature()
            self.diode1_current, self.diode2_current = self.query_diode_current()
            self.lbo_temp = self.query_lbo_temperature()
            self.etalon_temp = self.query_etalon_temperature()
            self.set_temps_label.setText(f"Diode 1: {self.set_temps[0]} °C \nDiode 2: {self.set_temps[1]} °C \nLBO: {self.set_temps[2]} °C \nEtalon: {self.set_temps[3]} °C")
            self.diode1_temp_label.setText(f"Diode 1 Temp: {self.diode1_temp} °C")
            self.diode2_temp_label.setText(f"Diode 2 Temp: {self.diode2_temp} °C")
            self.diode1_heatsink_temp_label.setText(f"Diode 1 Heatsink Temp: {self.diode1_heatsink_temp} °C")
            self.diode2_heatsink_temp_label.setText(f"Diode 2 Heatsink Temp: {self.diode2_heatsink_temp} °C")
            self.baseplate_temp_label.setText(f"Baseplate Temp: {self.baseplate_temp} °C")
            self.diode1_current_label.setText(f"Diode 1 Current: {self.diode1_current} mA")
            self.diode2_current_label.setText(f"Diode 2 Current: {self.diode2_current} mA")
            self.lbo_temp_label.setText(f"LBO Temp: {self.lbo_temp} °C")
            self.etalon_temp_label.setText(f"Etalon Temp: {self.etalon_temp} °C")
        
            self.shutter_label.setText(f"Shutter: {shutter_status}")
            self.laser_status_label.setText(f"Laser Status: {laser_status}")
            self.power_label.setText(f"Power: {power_status} mW")
            self.wavelength_label.setText(f"Wavelength: {wavelength_status} nm")
            self.humidity_label.setText(f"Humidity: {humidity_status} %")
            self.modelocked_label.setText(f"Modelocked: {modelocked_status}")

            self.open_shutter_button.clicked.connect(self.open_shutter)
            self.close_shutter_button.clicked.connect(self.close_shutter)

  #          self.start_logging()

        except serial.SerialException as e:
            QMessageBox.critical(self, "Connection Error", str(e))
            self.status_label.setText("Status: Not connected")
        



    def start_logging(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(self.update_time)  # Update every second (1000 ms)
       
    def update_data(self):
        power_list = []
        datetime_list = []
        #with self.ser as self.ser:
          #  shutter_status = query_shutter(ser))
           # laser_status = query_laser_on(ser))
        self.diode1_temp, self.diode2_temp = self.query_diode_temperature()
        self.diode1_heatsink_temp, self.diode2_heatsink_temp = self.query_diode_heatsink_temperature()  
        self.baseplate_temp = self.query_baseplate_temperature()
        self.diode1_current, self.diode2_current = self.query_diode_current()
        self.lbo_temp = self.query_lbo_temperature()
        self.etalon_temp = self.query_etalon_temperature()
        self.current_power = self.query_power()
        self.instantaneous_data = [self.current_power, self.baseplate_temp, self.diode1_temp, self.diode2_temp,
                                    self.diode1_heatsink_temp, self.diode2_heatsink_temp, self.lbo_temp,
                                    self.etalon_temp, self.diode1_current, self.diode2_current]
        if len(self.data) < self.array_length:

            for idx, _ in enumerate(self.instantaneous_data):
                self.data[idx].append(float(self.instantaneous_data[idx]))

            self.timestamps.append(datetime.now())
        else:
            for idx, _ in enumerate(self.temp_current_data):
                self.temp_current_data[idx][:-1] = self.temp_current_data[idx][1:]
                self.temp_current_data[idx][-1] = float(self.instantaneous_data[idx])
    
            self.timestamps[:-1] = self.timestamps[1:] 
            self.timestamps[-1] = datetime.now()


        humidity_status = self.query_humidity()
    
        self.diode1_temp_label.setText(f"Diode 1 Temp: {self.diode1_temp} °C")
        self.diode2_temp_label.setText(f"Diode 2 Temp: {self.diode2_temp} °C")
        self.diode1_heatsink_temp_label.setText(f"Diode 1 Heatsink Temp: {self.diode1_heatsink_temp} °C")
        self.diode2_heatsink_temp_label.setText(f"Diode 2 Heatsink Temp: {self.diode2_heatsink_temp} °C")
        self.baseplate_temp_label.setText(f"Baseplate Temp: {self.baseplate_temp} °C")
        self.diode1_current_label.setText(f"Diode 1 Current: {self.diode1_current} mA")
        self.diode2_current_label.setText(f"Diode 2 Current: {self.diode2_current} mA")
        self.lbo_temp_label.setText(f"LBO Temp: {self.lbo_temp} °C")
        self.etalon_temp_label.setText(f"Etalon Temp: {self.etalon_temp} °C")
    
        self.power_label.setText(f"Power: {self.current_power} mW")
        self.humidity_label.setText(f"Humidity: {humidity_status} %")


        self.power_trace.setData(x=[x.timestamp() for x in self.timestamps], y=self.data[0])  # Update the plot with new power data
        # Update the temperature and current plot
        for idx, trace in enumerate(self.temp_current_traces):

            trace.setData(x=[x.timestamp() for x in self.timestamps], y=self.data[idx+1])


        if self.arduino.is_open: #avoid a hard crash if the arduino gets unplugged
            self.room_temp, self.room_humidity = self.query_arduino_sensor()
            self.room_temp_label.setText(f"Room Temperature: {self.room_temp} °C")
            self.room_humidity_label.setText(f"Room Humidity: {self.room_humidity} %")  
            self.room_data[0].append(float(self.room_temp))
            self.room_data[1].append(float(self.room_humidity))
            for idx, trace in enumerate(self.room_data_traces):
                trace.setData(x=[x.timestamp() for x in self.timestamps], y=self.room_data[idx])    

        with open('power_log.txt', 'a') as f:

            data_line = str(self.timestamps[-1])+','+','.join(str(i) for i in self.instantaneous_data) + ',' + str(self.room_temp) + ',' + str(self.room_humidity)

            f.write(f"{data_line}\n")


    def query_shutter(self):
        self.ser.write('?S\r\n'.encode('utf-8'))  # Send command to the device
        response = self.ser.readline().decode('utf-8').strip()
        if response == '0':
            response = 'Shutter closed.'
        elif response == '1':
            response = 'Shutter open.'
        return response

    def open_shutter(self):
        with self.ser as self.ser:
            if not self.ser.is_open:
                self.ser.open()
            self.ser.write('S=1\r\n'.encode('utf-8'))  # Send command to open the shutter
            response = self.ser.readline().decode('utf-8').strip()  # Read the response
            shutter_state = self.query_shutter()
            self.shutter_label.setText(f"Shutter: {shutter_state}")
        return

    def close_shutter(self):
        with self.ser as self.ser:
            if not self.ser.is_open:
                self.ser.open()
            self.ser.write('S=0\r\n'.encode('utf-8'))  # Send command to close the shutter
            response = self.ser.readline().decode('utf-8').strip()  # Read the response
            shutter_state = self.query_shutter()
            self.shutter_label.setText(f"Shutter: {shutter_state}")
        return

    def query_laser_on(self):
        self.ser.write('?L\r\n'.encode('utf-8'))  # Send command to the device
        response = self.ser.readline().decode('utf-8').strip()  # Read the response
        if response == '0': 
            response = 'Laser off.'
        elif response == '1': 
            response = 'Laser on.'
        return response

    def query_power(self):
        self.ser.write('?UF\r\n'.encode('utf-8'))  # Send command to the device
        response = self.ser.readline().decode('utf-8').strip()  # Read the response in mW
        return float(response)

    def query_faults(self):
        self.ser.write('?F\r\n'.encode('utf-8'))  # Send command to the device
        response = self.ser.readline().decode('utf-8').strip()  # Read the response
        return response

    def query_baseplate_temperature(self):
        self.ser.write('?BT\r\n'.encode('utf-8'))
        response = self.ser.readline().decode('utf-8').strip()
        return response

    def query_diode_temperature(self):
        self.ser.write('?D1T\r\n'.encode('utf-8'))
        response1 = self.ser.readline().decode('utf-8').strip()
        self.ser.write('?D2T\r\n'.encode('utf-8'))  # Send command to the device
        response2 = self.ser.readline().decode('utf-8').strip()
        return (response1, response2)

    def query_diode_heatsink_temperature(self):
        self.ser.write('?D1HST\r\n'.encode('utf-8'))
        response1 = self.ser.readline().decode('utf-8').strip() # Read the response     
        self.ser.write('?D2HST\r\n'.encode('utf-8'))  # Send command to the device
        response2 = self.ser.readline().decode('utf-8').strip()  # Read the response
        return (response1, response2)

    def query_diode_current(self):
        self.ser.write('?D1C\r\n'.encode('utf-8'))
        response1 = self.ser.readline().decode('utf-8').strip()
        self.ser.write('?D2C\r\n'.encode('utf-8'))  
        response2 = self.ser.readline().decode('utf-8').strip()
        return (response1, response2)

    def query_lbo_temperature(self):
        self.ser.write('?LBOT\r\n'.encode('utf-8'))
        response = self.ser.readline().decode('utf-8').strip()
        return response

    def query_etalon_temperature(self):
        self.ser.write('?ET\r\n'.encode('utf-8'))
        response = self.ser.readline().decode('utf-8').strip()
        return response 

    def query_set_temperatures(self):
        self.ser.write('?D1ST\r\n'.encode('utf-8'))
        diode1set_temp = self.ser.readline().decode('utf-8').strip()  # Read the response
        self.ser.write('?D2ST\r\n'.encode('utf-8'))  # Send command to the device
        diode2set_temp = self.ser.readline().decode('utf-8').strip()  # Read the response
        self.ser.write('?LBOST\r\n'.encode('utf-8'))  # Send command to the device
        lbo_set_temp = self.ser.readline().decode('utf-8').strip()  # Read the response
        self.ser.write('?EST\r\n'.encode('utf-8'))  # Send command to the device
        etalon_set_temp = self.ser.readline().decode('utf-8').strip()  # Read the response
        return (diode1set_temp, diode2set_temp, lbo_set_temp, etalon_set_temp)

    def query_wavelength(self):
        self.ser.write('?VW\r\n'.encode('utf-8'))  # Send command to the device
        response = self.ser.readline().decode('utf-8').strip()  # Read the response
        return response

    def query_humidity(self):
        self.ser.write('?RH\r\n'.encode('utf-8'))  # Send command to the device
        response = self.ser.readline().decode('utf-8').strip()  # Read the response
        return response

    def query_modelocked(self):
        self.ser.write('?MDLK\r\n'.encode('utf-8'))  # Send command to the device
        response = self.ser.readline().decode('utf-8').strip()  # Read the response
        return response


#should probably make two different classes for the laser and the arduino, but whatever

    def query_arduino_sensor(self):

        self.arduino.write('READ\r\n'.encode('utf-8'))
        response = self.arduino.readline().decode('utf-8').strip()

        temp, humidity = response.split(',')

        return (temp, humidity)



if __name__ == "__main__":
    app = QApplication([])
    window = PowerLoggerApp()
    window.show()
    app.exec()

