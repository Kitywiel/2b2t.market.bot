// Optional tiny webserver to keep Replit or uptime monitors happy.
const express = require("express");
const app = express();

app.get("/", (req, res) => res.send("OK"));

const port = process.env.PORT || 3000;
app.listen(port, () => {
  console.log(`Keep-alive server listening on ${port}`);
});