from database import Database
import json
import time
import datetime
from time import gmtime, strftime
import plotly
import plotly.plotly as py
from plotly.graph_objs import *

plotly.tools.set_credentials_file(username='kmatsudo', api_key='En9O6dgqc7dXPsKdL2EY')



class Prototype:
    def __init__(self):
        
        self.local_database = Database("accounts")
        self.local_database.load_json_database()
        self.local_database.add_user("kenny");
        self.local_database.add_reminder("kenny","tuesday","10","44","Work on project")
        
        

    def print_json(self):
        pretty = (self.local_database.data_list)
        print(json.dumps(pretty,indent=3))



   
     
if __name__ == "__main__":
    heller = Prototype()
    print(datetime.datetime.now().time())
    print(time.strftime("%H:%M:%S",gmtime()))

    trace0 = Scatter(
            x=[1,2,3,4,5,6,7,8,9,10],
            y=[150,148,151,149,150,150,150,151,152,153,180]
            )



    data = Data([trace0])

    py.plot(data,filename = 'basic-line')
