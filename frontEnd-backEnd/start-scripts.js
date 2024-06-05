// start-scripts.js

const { spawn } = require('child_process');
const os = require('os');
const path = require('path');

const commands = [
  'node backend.js',
  'node bckend22.js',
  'http-server -p 3030',
  'http-server -p 8000',
];

const openHTMLFilesWithDelay = () => {
  const htmlFiles = ['site_admin_2.html', 'site.html'];

  const openFile = (file) => {
    const filePath = path.resolve(__dirname, file);

    if (os.platform() === 'win32') {
      // On Windows, use 'start' command
      spawn('cmd.exe', ['/c', `start "" "${filePath}"`], { stdio: 'inherit', shell: true });
    } else {
      // On macOS/Linux, use 'open' command
      spawn('open', [filePath], { stdio: 'inherit', shell: true });
    }
  };

  htmlFiles.forEach((file, index) => {
    // Introduce a delay of 5 seconds for the first HTML file, and 2 seconds for the rest (adjust as needed)
    const delay = index === 0 ? 5000 : index * 5000;
    setTimeout(() => {
      openFile(file);
    }, delay);
  });
};


const runCommandInNewTerminal = (command) => {
  if (os.platform() === 'win32') {
    // On Windows, use 'start' command
    spawn('cmd.exe', ['/c', 'start', 'cmd.exe', '/k', command], { stdio: 'inherit', shell: true });
  } else {
    // On Linux, use 'gnome-terminal' command (you might need to adjust for other desktop environments)
    spawn('gnome-terminal', ['-e', command], { stdio: 'inherit', shell: true });
  }
};

const runAllCommandsInNewTerminals = () => {
  openHTMLFilesWithDelay();

  commands.forEach((command) => {
    runCommandInNewTerminal(command);
  });

  console.log('All commands started. Press Ctrl+C to terminate.');
};

runAllCommandsInNewTerminals();
