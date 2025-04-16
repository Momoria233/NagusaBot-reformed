const fs = require('fs');
const path = require('path');

const directoryPath = path.join(__dirname, 'yulu');
const jsonFilePath = path.join(__dirname, 'yulu.json');

fs.readdir(directoryPath, (err, files) => {
  if (err) {
    return console.error('Unable to scan directory: ' + err);
  }

  const jsonContent = JSON.stringify(files, null, 4);

  fs.writeFile(jsonFilePath, jsonContent, 'utf8', (err) => {
    if (err) {
      return console.error('Error writing file: ' + err);
    }

    console.log('Successfully wrote file');
  });
});