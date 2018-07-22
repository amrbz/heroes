HEROES API
---
A guide to run heroes game API server

1. Copy *docker-compose.prod.yml* to your server
2. Run ```docker-compose up -d```
3. In your browser open: http://localhost:4200
4. Using Crate database console create tables from *./server/schema.sql* file
5. Insert initial data to Clans, Mines and Units tables (use [Postman](https://www.getpostman.com/) or similar app)