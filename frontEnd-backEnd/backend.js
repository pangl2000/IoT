const express = require('express');
const cors = require('cors');
const axios = require('axios');
const bodyParser = require('body-parser');

const app = express();
const server = require('http').createServer(app);
const stations = [];
const buses = [];
let congestions = [];
let busdata = [];
const XLSX = require('xlsx');
const fs = require('fs');

const workbook = XLSX.readFile('Routes.xlsx');

const sheetName = workbook.SheetNames[0];
const worksheet = workbook.Sheets[sheetName];

app.use(bodyParser.json());

app.use(cors({
    origin: '*',
    credentials: true,
    allowedHeaders: ['Content-Type', 'Authorization'],
}));

async function readexcel(){
  const startRow = 1; 
  const endRow = 123;  
  const Cols = ['C','E','F','G','H','I','J','K'];

  const parsedData = [];

  for (let rowNum = startRow; rowNum <= endRow; rowNum++) {
      const row = [];
      let f = true;
      for (let col of Cols) {
          const cellAddress = { c: XLSX.utils.decode_col(col), r: rowNum };
          const cellRef = XLSX.utils.encode_cell(cellAddress);
          const cell = worksheet[cellRef];
          if (cell && cell.w !== '-') {
              row.push(cell.w);
          } else {
              f=false;
              continue;
          }
      }
      if (f){
        parsedData.push(row);
      }
      
  }
  console.log(parsedData);
  return parsedData;
}

app.get('/getalltheroutes', async (req, res) => {
  try {
      const parsedData = await readexcel(req.query.id);
      res.json(parsedData);
  } catch (error) {
      console.error('Error:', error.message);
      res.status(500).json({ error: 'Internal Server Error' });
  }
});

const readEntityAttribute = async (entityId, attributeName) => {
  try {
    const response = await axios.get(`http://150.140.186.118:1026/v2/entities/${entityId}`);
    
    console.log('Full response:', response.data);

    if (response.data && response.data[attributeName]) {
      const attributeValue = response.data[attributeName].value;
      /* console.log(`Attribute ${attributeName} value:`, attributeValue); */
      return attributeValue;
    } else {
      console.log(`Attribute ${attributeName} not found for entity ${entityId}`);
      return null;
    }
  } catch (error) {
    console.error(`Error reading entity attribute ${attributeName}:`, error.message);
    return null;
  }
};

const readStationsLBinfo = async (entityId) => {
  try {
      const dT = await readEntityAttribute(entityId, 'dateLastReported');
      const l = await readEntityAttribute(entityId, "vehicleLastReported");
      len =("urn:ngsild:Vehicle:Bus:").length;
      cf = "urn:ngsild:CrowdFlowObserved:Bus:"+(l.value).slice(len, (l.value).length);
      const lb = await readEntityAttribute(cf, "alternateName");

      //console.log("name", await readEntityAttribute((await readEntityAttribute(entityId, "crowdFlowObserved")).value, 'name'));
      return {
          dateTime: dT,
          lastbus: lb,
      };
      
  }catch (error) {
      console.error(`Error in readBusPCinfo ${entityId} :`, error.message);
      return null;
  }
}

app.get('/getStationsLB', async (req, res) => {
  try {
      const stationlasts = await readStationsLBinfo(req.query.id);
      console.log(stationlasts);
      res.json(stationlasts);
  } catch (error) {
      console.error('Error:', error.message);
      res.status(500).json({ error: 'Internal Server Error' });
  }
});

app.get('/getBusDirection', async (req, res) => {
  try {
      const laststation = await readEntityAttribute(req.query.id, 'name');
      console.log(laststation);
      res.json(laststation);
  } catch (error) {
      console.error('Error:', error.message);
      res.status(500).json({ error: 'Internal Server Error' });
  }
});


app.get('/getStationInfo', async (req, res) => {
    console.log('GET /getStationInfo called');
    res.json(stationData);
});

app.get('/getBusInfo', async (req, res) => {
    res.json(busData);
});

app.get('/googlemaps', async (req, res) => {
  try {
    const { origin, destination, mode, key } = req.query;
    const apiUrl = `https://maps.googleapis.com/maps/api/directions/json?origin=${origin}&destination=${destination}&mode=${mode}&key=${key}`;
    
    const response = await axios.get(apiUrl);
    res.json(response.data);
  } catch (error) {
    console.error('Error:', error.message);
    res.status(500).json({ error: 'Internal Server Error' });
  }
});


const updateStationData = async () => {
    try {
        stationData = await Promise.all(stations.map(async (station) => {
            return {
                id: station,
                location: await readEntityAttribute(station, 'location'),
                name: await readEntityAttribute(station, 'name')
            };
            
        }));
    } catch (error) {
        console.error('updateStationData Error updating station data:', error.message);
    }
};

  const updateBusData = async () => {
    try {
        busData = await Promise.all(buses.map(async (bus) => {
            const cf = await readEntityAttribute(bus, 'crowdFlowObserved');
            const congested = await readEntityAttribute(cf.value, 'congested');
            const locationData = await readEntityAttribute(bus, 'location');
            const disc = await readEntityAttribute(bus, 'description');
            
            if (!locationData) {
                return;
            }
            
            return {
                id: bus,
                location: locationData,
                congested: congested.value,
                crowdflowid: cf.value,
                description: disc.value
            };
                
        }));

          const filteredbuss = busdata.filter(bus => bus.congested === true && !congestions.includes(bus.id));
          const removebuss = busdata.filter(bus => bus.congested === false && congestions.includes(bus.id));
          congestions = congestions.filter(e => {
              !removebuss.map(bus => bus.id).includes(e);
          });

          filteredbuss.forEach(bus => {
              congestions.push(bus.id);
          });

      } catch (error) {
          console.error('Error updating station data:', error.message);
      }
  };

  const fData = async () => {
    try {
        for (let i = 1; i < 33; i++) {
            stations.push("urn:ngsild:TransportStation:Station:" + String(i));
            console.log(await readEntityAttribute(stations[i - 1], 'crowdFlowObserved'));
        }

        await updateStationData();

        app.get('/getStationInfo', async (req, res) => {
            console.log('GET /getStationInfo called');
            res.json(stationData);
        });

        

        for (let i = 1; i < 4; i++) {
            buses.push("urn:ngsild:Vehicle:Bus:" + String(i));
            console.log(await readEntityAttribute(buses[i-1], "crowdFlowObserved"));
        }
        await updateBusData();

        app.get('/getBusInfo', async (req, res) => {
            res.json(buses);
        });

    } catch (error) {
        console.error('Error in fData:', error.message);
    }
};
fData();
console.log("kkkkkk",buses);

  const PORT = 3000;
  server.listen(PORT, () => {
    console.log(`Server running at http://localhost:${PORT}/`);
  });

