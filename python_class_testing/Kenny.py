from database import Database
import json
import plotly
import plotly.plotly as py
from plotly.graph_objs import *

plotly.tools.set_credentials_file(username='kmatsudo', api_key='En9O6dgqc7dXPsKdL2EY')



class Prototype:
    def __init__(self):
        
        self.local_database = Database("accounts")
        self.local_database.load_json_database()
        self.local_database.add_user("kenny",str(4056));
        self.local_database.add_reminder("kenny","tuesday","10","44","Work on project")
        
        

    def print_json(self):
        pretty = (self.local_database.data_list)
        print(json.dumps(pretty,indent=3))

    def get_weight(self):
        print(self.local_database.data_list["users"]["kenny"]["log_history"])
    
   
     
if __name__ == "__main__":
    heller = Prototype()
    heller.print_json()

    heller.get_weight()
  
    plotly.offline.plot({
            "data": [Scatter(x=[1,2,3,4,5,6,7,8,9,10], y=[150,148,151,149,150,150,150,151,152,153,180])],
            "layout": Layout(title="WeightGraph")
        },auto_open=False)

