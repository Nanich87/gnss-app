from guizero import App, Text, TextBox, Box, PushButton, MenuBar, yesno
from threading import Thread
import pynmea2, socket, time, os, logging

project_path = ""
project_ext = ".txt"
instrument_height = 2.0
connected = False
measure = False
separator = ","

logging.basicConfig(filename='app.log', filemode='w', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def createProject():
    file = app.question("New Project", "Enter file name:")
    if file is not None:
        project_path = file + project_ext
        current_dir = os.path.dirname(os.path.realpath(__file__))
        full_path = os.path.join(current_dir, project_path)
        open(full_path,"w").close()
        setCurrentProject(full_path)
        
def openProject():
    file = app.select_file(title="Select project", folder=".", filetypes=[["Text files", "*.txt"]], save=False)
    if file is not None:
        setCurrentProject(file)

def setCurrentProject(path):
    project_path = path
    text_project.value = project_path

def closeApp():
    if yesno("Close", "Do you want to quit?"):
        app.destroy()

def about():
    app.info("Land Survey", "Open source app for Land Surveyors")

def updateLocation(gga):
    input_latitude.value = gga.lat
    input_longitude.value = gga.lon
    input_altitude.value = "{:.3f}".format(gga.altitude + float(gga.geo_sep) - instrument_height)
    input_satellites.value = gga.num_sats
    input_age.value = gga.age_gps_data
    input_solution.value = gga.gps_qual 

def updateRmse(gst):
    input_rmse_latitude.value = "{:.3f}".format(gst.std_dev_latitude)
    input_rmse_longitude.value = "{:.3f}".format(gst.std_dev_longitude)
    input_rmse_altitude.value = "{:.3f}".format(gst.std_dev_altitude)

def updateDop(gsa):
    input_pdop.value = gsa.pdop
    input_hdop.value = gsa.hdop
    input_vdop.value = gsa.vdop

def toggleLocation(state):
    input_latitude.enabled = state
    input_longitude.enabled = state
    input_altitude.enabled = state
    input_satellites.enabled = state
    input_age.enabled = state
    input_solution.enabled = state

def toggleRmse(state):
    input_rmse_latitude.enabled = state
    input_rmse_longitude.enabled = state
    input_rmse_altitude.enabled = state

def toggleDop(state):
    input_pdop.enabled = state
    input_hdop.enabled = state
    input_vdop.enabled = state

def connectTcpThread():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("localhost", 27100))

        global connected
        while connected:
            data = s.recv(1024)
            if not data:
                continue
            
            global measure
            if measure == True:
                toggleLocation(False)
                toggleRmse(False)
                toggleDop(False)

            text = data.decode("utf-8")
            messages = text.splitlines()

            gga = None
            gsa = None
            gst = None

            for message in messages:
                try:
                    msg = pynmea2.parse(message)
                    if isinstance(msg, pynmea2.GGA):
                        gga = msg
                        updateLocation(msg)
                    elif isinstance(msg, pynmea2.GSA) and gsa is None:
                        gsa = msg
                        updateDop(msg)
                    elif isinstance(msg, pynmea2.GST):
                        gst = msg
                        updateRmse(msg)
                    else:
                        continue
                except pynmea2.ParseError as e:
                    logging.error('Parse error: %s', e)
                    continue

            if measure == True:
                pdop = 0.0
                hdop = 0.0
                vdop = 0.0
                    
                if gsa is not None:
                    pdop = gsa.pdop
                    hdop = gsa.hdop
                    vdop = gsa.vdop

                std_dev_latitude = 0.0
                std_dev_longitude = 0.0
                std_dev_altitude = 0.0

                if gst is not None:
                    std_dev_latitude = gst.std_dev_latitude
                    std_dev_longitude = gst.std_dev_longitude
                    std_dev_altitude = gst.std_dev_altitude

                if project_path is not None and os.path.exists(project_path):
                    with open(project_path, 'a') as project:
                        project.write(gga.timestamp.strftime('%H:%M:%S') + separator +
                                      gga.lat + separator +
                                      gga.lon + separator +
                                      str(gga.altitude) + separator +
                                      gga.geo_sep + separator +
                                      str(instrument_height) + separator +
                                      str(gga.gps_qual) + separator +
                                      str(gga.num_sats) + separator +
                                      str(gga.age_gps_data) + separator +
                                      str(pdop) + separator +
                                      str(hdop) + separator +
                                      str(vdop) + separator +
                                      str(std_dev_latitude) + separator +
                                      str(std_dev_longitude) + separator +
                                      str(std_dev_altitude) + '\n')
                
                time.sleep(1)
                measure = False
                
                button_measure.enabled = True
                
                toggleLocation(True)
                toggleRmse(True)
                toggleDop(True)
                
        s.close()
    except:
        logging.exception("Fatal error in TCP thread", exc_info=True)
        app.error("Error", "Cannot connect to device!")
    finally:
        connected = False
        button_connect.text = "Connect"

def setInstrumentHeight():
    try:
        global instrument_height
        instrument_height = float(input_instrument_height.value)
        app.info("Information", "Instrument height successfully set!")
    except:
        logging.exception("Fatal error in setting instrument height", exc_info=True)
        app.error("Error", "Invalid instrument height!")

def connectDevice():
    global connected
    if connected == True:
        connected = False
    else:
        connected = True
        
        tcp_thread = Thread(target = connectTcpThread)
        tcp_thread.start()

        button_connect.text = "Disconnect"

def savePoint():
    if connected == False:
        app.info("Warning", "Device is not connected!")
        return
    
    global measure
    measure = True
    button_measure.enabled = False

app = App(title="Land Survey", width=500, height=400)
#app.tk.attributes("-fullscreen", True)

menubar = MenuBar(app,
                  toplevel=["File", "Help"],
                  options=[
                      [ ["New", createProject], ["Open", openProject], ["Exit", closeApp] ],
                      [ ["About", about] ]
                  ])

# Set up instrument height
instrument_setup_box = Box(app, width="fill", align="top")

text_instrument_height = Text(instrument_setup_box, text="Instrument Height:", align="left")
input_instrument_height = TextBox(instrument_setup_box, text="{:.3f}".format(instrument_height), align="left")
text_height_unit = Text(instrument_setup_box, text="m", align="left")
button = PushButton(instrument_setup_box, text="Set", padx=20, command=setInstrumentHeight, align="right")

# Measure
buttons_box = Box(app, width="fill", align="bottom")

button_connect = PushButton(buttons_box, text="Connect", command=connectDevice, align="left")
text_project = Text(buttons_box, text="No project selected", align="bottom")
button_measure = PushButton(buttons_box, text="Measure", command=savePoint, align="right")

# DOP
dop_box = Box(app, height="fill", align="right")
dop_inner_box = Box(dop_box, layout="grid", align="top")

text_pdop = Text(dop_inner_box, text="PDOP:", align="left", grid=[0,0])
text_hdop = Text(dop_inner_box, text="HDOP:", align="left", grid=[0,1])
text_vdop = Text(dop_inner_box, text="VDOP:", align="left", grid=[0,2])

input_pdop = TextBox(dop_inner_box, text="---", grid=[1,0])
input_hdop = TextBox(dop_inner_box, text="---", grid=[1,1])
input_vdop = TextBox(dop_inner_box, text="---", grid=[1,2])

# Location
location_box = Box(app, width="fill", align="top")
location_inner_box = Box(location_box, layout="grid", align="left")

## 3D Position
text_latitude = Text(location_inner_box, text="Latitude:", align="left", grid=[0,0])
text_longitude = Text(location_inner_box, text="Longitude:", align="left", grid=[0,1])
text_latitude = Text(location_inner_box, text="Altitude:", align="left", grid=[0,2])

input_latitude = TextBox(location_inner_box, width="fill", text="---", grid=[1,0])
input_longitude = TextBox(location_inner_box, width="fill", text="---", grid=[1,1])
input_altitude = TextBox(location_inner_box, width="fill", text="---", grid=[1,2])

## RMS
text_rmse_latitude = Text(location_inner_box, text="RMS Latitude:", align="left", grid=[0,3])
text_rmse_longitude = Text(location_inner_box, text="RMS Longitude:", align="left", grid=[0,4])
text_rmse_latitude = Text(location_inner_box, text="RMS Altitude:", align="left", grid=[0,5])

input_rmse_latitude = TextBox(location_inner_box, width="fill", text="---", grid=[1,3])
input_rmse_longitude = TextBox(location_inner_box, width="fill", text="---", grid=[1,4])
input_rmse_altitude = TextBox(location_inner_box, width="fill", text="---", grid=[1,5])

## Other
text_satellites = Text(location_inner_box, text="Satellites:", align="left", grid=[0,6])
text_age = Text(location_inner_box, text="Age:", align="left", grid=[0,7])
text_solution = Text(location_inner_box, text="Solution:", align="left", grid=[0,8])

input_satellites = TextBox(location_inner_box, width="fill", text="---", grid=[1,6])
input_age = TextBox(location_inner_box, width="fill", text="---", grid=[1,7])
input_solution = TextBox(location_inner_box, width="fill", text="---", grid=[1,8])

app.display()
