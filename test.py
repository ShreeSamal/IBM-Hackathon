#write pyton code to convert a string timestamp to dd/mm/yyyy format
#input: 1693247400
#output: 27/05/2023
import datetime
timestamp = 1693247400
dt_object = datetime.datetime.fromtimestamp(timestamp)
print(dt_object.strftime("%d/%m/%Y"))