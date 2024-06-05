const express = require('express');
const cors = require('cors');
const axios = require('axios');
const bodyParser = require('body-parser');
const fetch = require('node-fetch');
const http = require('http');

const app = express();
const server = http.createServer(app);
const nodemailer = require('nodemailer');

const PORT = 8080;

const stations = [];
const buses = [];
let stationData = [];
let busData = [];
let buslasts = [];
let violations = [];
let congestions = [];

app.use(bodyParser.json());
app.use(cors({
    origin: '*',
    credentials: true,
    allowedHeaders: ['Content-Type', 'Authorization'],
}));

const transporter = nodemailer.createTransport({
    pool: true,
    service: 'hotmail',
    auth: {
      user: 'evgenia.123@hotmail.com',
      pass: '-',
    },
    tls: {
        rejectUnauthorized: false
    }
});



app.get('/getStationInfo', async (req, res) => {
    console.log('GET /getStationInfo called');
    res.json(stationData);
});
app.get('/getBusInfo', async (req, res) => {
    res.json(busData);
}); 

const readBusPCinfo = async (entityId) => {
    try {
        
        const lS = await readEntityAttribute((await readEntityAttribute(entityId, "crowdFlowObserved")).value, 'name');
        const dT = await readEntityAttribute((await readEntityAttribute(entityId, "crowdFlowObserved")).value, 'dateObserved');
        const pC = await readEntityAttribute((await readEntityAttribute(entityId, "crowdFlowObserved")).value, 'peopleCount');
        console.log("name", await readEntityAttribute((await readEntityAttribute(entityId, "crowdFlowObserved")).value, 'name'));
        return {
            lastStation: lS,
            dateTime: dT,
            peopleCount: pC
        };
        
    }catch (error) {
        console.error(`Error in readBusPCinfo ${entityId} :`, error.message);
        return null;
    }
}

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

app.get('/getBusPC', async (req, res) => {
    try {
        const buslasts = await readBusPCinfo(req.query.id);
        console.log(buslasts);
        res.json(buslasts);
    } catch (error) {
        console.error('Error:', error.message);
        res.status(500).json({ error: 'Internal Server Error' });
    }
});

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

const readEntityAttribute = async (entityId, attributeName) => {
    try {
      const response = await axios.get(`http://150.140.186.118:1026/v2/entities/${entityId}`);
      
      //console.log('Full response:', response.data[attributeName]);
  
      if (response.data && response.data[attributeName]) {
        const attributeValue = response.data[attributeName].value;
        /* console.log(`Attribute ${attributeName} value:`, attributeValue); */
        return attributeValue;
      } else {
        console.log(`Attribute ${attributeName} not found for entity ${entityId}`);
        return null;
      }
    } catch (error) {
      console.error(`Error reading entity attribute ${entityId} ${attributeName}:`, error.message);
      return null;
    }
};
const monitorAttribute = async (stationids) => {
    let text='';
    try {
        console.log("opopop");
        
        //console.log(readEntityAttribute(await readEntityAttribute(stationids[0], 'trafficViolation')));
        await Promise.all(stationids.map(async (id) => {
            
            try {
                const observationDateTime = await readEntityAttribute((await readEntityAttribute(id, "trafficViolation")).value, 'observationDateTime');
                const vehiclePlate = await readEntityAttribute((await readEntityAttribute(id, "trafficViolation")).value, 'vehiclePlate');
                const transportStation = await readEntityAttribute(id, 'name');

                text = text + `Illegal parking detected in ${transportStation.value} at ${observationDateTime.value['@value']}. The vehicle of interest has the following plate number: ${vehiclePlate}.\n\n`;
            } catch (attributeError) {
                console.log(id);
                console.log(await readEntityAttribute((await readEntityAttribute(id, "trafficViolation")).value, 'observationDateTime'), "+");

                console.error(`Error fetching attributes for station ${id}:`, attributeError);
                
            }
        }));
        
        const mailOptions = {
            from: 'evgenia.123@hotmail.com',
            to: null,
            subject: 'Illegal parking in bus station',
            text: text,
        };

        setTimeout(() => {
            transporter.sendMail(mailOptions, (error, info) => {
                if (error) {
                    console.error('Error sending email:', error);
                } else {
                    console.log('Email sent:', info.response);
                    violations.push(filteredStations);
                }
            });
        }, 10000);
    } catch (error) {
        console.error('Error monitoring attribute:', error);
    }
};

app.post('/notification-endpoint', async (req, res) => {
    console.log('Received notification:', req.body);
    const subscriptionData = req.body; 
    const contextBrokerUrl = 'http://150.140.186.118:1026/v2/subscriptions';

    try {
        const response = await fetch(contextBrokerUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(subscriptionData),
        });

        const responseData = await response.text();

        if (!responseData || !response.headers.get('content-type')?.includes('application/json')) {
            console.log('Unexpected or empty response:', responseData);
            res.status(500).json({ error: 'Unexpected or empty response from Orion Context Broker' });
            return;
        }

        const jsonResponse = JSON.parse(responseData);
        res.json(jsonResponse);
    } catch (error) {
        console.error('Error:', error);
        res.status(500).json({ error: 'Internal Server Error' });
    }
});






const updateStationData = async () => {
    try {
        stationData = await Promise.all(stations.map(async (station) => {
            //const illparkingid = await readEntityAttribute(station, 'trafficViolation') || '_';
            const illparkingid = await readEntityAttribute(station, 'trafficViolation') || '_';
            return {
                id: station,
                crowdflowid: await readEntityAttribute(station, 'crowdFlowObserved'),
                illparkingid: illparkingid,
                location: await readEntityAttribute(station, 'location'),
                name: await readEntityAttribute(station, 'name')
            };
            
        }));

        const filteredStations = stationData.filter(station => station.illparkingid.value !== '_' && !violations.includes(station.id));
        const removeStations = stationData.filter(station => station.illparkingid.value === '_' && violations.includes(station.id));
        violations = violations.filter(e => !removeStations.map(station => station.id).includes(e));
        
        console.log("pppppp");
        filteredStations.forEach(station => {
            violations.push(station.id);
        });
        monitorAttribute(violations);

    } catch (error) {
        console.error('updateStationData Error updating station data:', error.message);
    }
};


const updateBusData = async () => {
    try {
        busData = await Promise.all(buses.map(async (bus) => {
            const congestedid = await readEntityAttribute(bus, 'crowdFlowObserved');
            const locationData = await readEntityAttribute(bus, 'location');
            if (!locationData) {
                return;
            }
            const number = await readEntityAttribute(bus, 'description');
            return {
                id: bus,
                description: number.value,
                location: locationData,
                crowdflowid: congestedid,
                license_plate: await readEntityAttribute(bus, 'license_plate')
            };
                
        }));

        const filteredbuss = busData.filter(bus => bus.congested === true && !congestions.includes(bus.id));
        const removebuss = busData.filter(bus => bus.congested === false && congestions.includes(bus.id));
        congestions = congestions.filter(e => {
            CongestionStopped(bus.id);
            !removebuss.map(bus => bus.id).includes(e);
        });

        filteredbuss.forEach(bus => {
            CongestedAllert(bus.id);
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


server.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});


   
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
                                                            /*Historical Data*/



      
const readDataByTime = async(req, res, entityId, initYear, initMonth, initDay, initHour, initMinute, initSecond,
    endYear, endMonth, endDay, endHour, endMinute, endSecond, tz_offset) => {
    console.log(`http://localhost:5003/entities_by_time/${entityId}/${Number(initYear)}/${Number(initMonth)}/${Number(initDay)}/${Number(initHour)}/${initMinute}/${initSecond}/${Number(endYear)}/${Number(endMonth)}/${Number(endDay)}/${Number(endHour)}/${endMinute}/${endSecond}/${tz_offset}`, typeof(entityId), typeof(endYear), typeof(initMinute));
    try {
        const response = await axios.get(`http://localhost:5003/entities_by_time/${entityId}/${initYear}/${initMonth}/${initDay}/${initHour}/${initMinute}/${initSecond}/${endYear}/${endMonth}/${endDay}/${endHour}/${endMinute}/${endSecond}/${tz_offset}`);

        const responseData = response.data;
    
        console.log('Type of responseData:', typeof responseData);
        console.log('Content of responseData:', responseData);
    
        const data = responseData.data;
    
        console.log('Type of data:', typeof data);
        console.log('Content of data:', data);
    
        const allEntries = Object.entries(data)
    
        const xValues = allEntries.map(([label, value]) => label);
        const yValues = allEntries.map(([label, value]) => value);
    
        res.json({ xValues, yValues });
    } catch (error) {
        console.error('Error fetching data from MongoDB:', error);
        res.status(500).json({ error: 'Internal server error' });
    }
};

const readDataAvgPeopleByTime = async(req, res, entityId, initYear, initMonth, initDay, initHour, initMinute, initSecond,
    endYear, endMonth, endDay, endHour, endMinute, endSecond, tz_offset) => {
    try {
      const response2 = await axios.get(`http://localhost:5003/avg_people_by_time/${entityId}/${initYear}/${initMonth}/${initDay}/${initHour}/${initMinute}/${initSecond}/${endYear}/${endMonth}/${endDay}/${endHour}/${endMinute}/${endSecond}/${tz_offset}`);

      const responseData2 = response2.data;
  
      const data2 = responseData2.data;
  
      console.log('Type of data2:', typeof data2);
      console.log('Content of data2:', data2);
  
      const entries2 = Object.entries(data2);
      const xValues2 = entries2.map(([label, value]) => label);
      const yValues2 = entries2.map(([label, value]) => value);
  
      console.log('Type of xValues2:', typeof xValues2);
      console.log('Content of xValues2:', xValues2);
      console.log('Type of yValues2:', typeof yValues2);
      console.log('Content of yValues2:', yValues2);
  
      res.json({ xValues2, yValues2 });
    } catch (error) {
      console.error('Error fetching data from MongoDB:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
};
      
  
app.get('/getDataByTime', async (req, res) => {
    try {
        const reqData = req.query;

        const data = await readDataByTime(
            req,
            res,
            reqData.id,
            Number(reqData.initYear),Number(reqData.initMonth),Number(reqData.initDay),Number(reqData.initHour),1,1,Number(reqData.endYear),Number(reqData.endMonth),Number(reqData.endDay),Number(reqData.endHour),2,2,0
            );
    } catch (error) {
    console.error('Error fetching data from MongoDB:', error);
    res.status(500).json({ error: 'Internal server error' });
    }
});

app.get('/getDataAvgPeopleByTime', async (req, res) => {
    try {
        const reqData = req.query;

        const data = await readDataAvgPeopleByTime(
            req,
            res,
            reqData.id,
            Number(reqData.initYear),Number(reqData.initMonth),Number(reqData.initDay),Number(reqData.initHour),1,1,Number(reqData.endYear),Number(reqData.endMonth),Number(reqData.endDay),Number(reqData.endHour),2,2,0
            );
    } catch (error) {
        console.error('Error fetching data from MongoDB:', error);
        res.status(500).json({ error: 'Internal server error' });
    }
});