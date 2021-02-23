# Lifo

This project is currently deployed completely on GCP. 

The project extensively rely on the following product on GCP:
Firebase, Cloud Run (both managed and on Anthos), Cloud functions,  Cloud SQL, GKE, CV API, Video Inteligence API

This frontend part was generated with [Angular CLI](https://github.com/angular/angular-cli) version 8.3.19.
The backend services are all micro-services based architecture, where each service is a docker container hosted on 
GCP cloud run, or a function hosted on Cloud functions. 
The use cases are Cloud Run and cloud functions are different: Cloud run are more full fledged REST API style services,
while functions are resource-light single functions. 
The client-facing data structures are mostly hosted by Firebase, where large object media files are hosted on Firestore,
both of whose backends are GCS object storage. 
The analytics data are stored on Cloud SQL for ease of reporting etc.
The ML related APIs (CV and video inteligence) are triggered by cloud functions to provide add-on analytics. 

### To Build protobuf dependencies
First make sure you have installed protoc according to the following tutorial/instructions:
https://github.com/protocolbuffers/protobuf

Basically we do NOT recommend you compile the binaries yourself, but instead, directly download a pre-compiled binary from:
https://github.com/protocolbuffers/protobuf/releases
Then, unzip the binary, copy the "protoc" binary to /usr/local/bin/protoc
Finally, add the following line to your .bashrc or .zshrc
alias protoc='/usr/local/bin/protoc'

Source .bashrc or .zshrc by running:
source .bashrc (or .zshrc)

You can test the protoc by running:
protoc

Once this is done, you can build the protobuf dependencies by running make under repo root:
cd /path/to/your/repo/influencer
make

This will create compiled protobuf code in each service directory.


### UI Deployment
##### Production hosting
To update remote production hosting, under project root folder, /influencer, run the following:
npm install & npm run build
firebase deploy --only hosting:lifo

##### Local development
To develop locally, under project root folder, /influencer, run the following:
npm install & npm start
This will launch a local server at localhost:4200

### Shopify APP
The Shopify app is mainly composed of two modules: app server, and client side scripts


### Nylas auth service
We leverage Nylas API products as documented here: https://docs.nylas.com/reference#introduction
The Nylas products provide a layer of abstraction for integrating both email and calendar for our customers. 

