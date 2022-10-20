/* This is passed to the Browser library via the jsextension
   parameter when the library is imported.

   This file will import all modules in the robot/<project
   name>/javascript folder. The code in this file is dependent on an
   environment variable named CCI_CONTEXT, which is initialized by the
   robot task.
*/

const fs = require("fs");

let cumulusci = require("cumulusci");
let cci_context = JSON.parse(process.env.CCI_CONTEXT);
cumulusci.project_config = cci_context.project_config;
cumulusci.org = cci_context.org;

// This is where each project should store their keywords.
// Maybe in the future this should be configurable, but for
// now it's not.
let javascript_dir = `${cci_context.project_config.repo_root}/robot/${cci_context.project_config.repo_name}/javascript`;

if (fs.existsSync(javascript_dir)) {
    // Should I put this in a try/catch? If I don't, we get a slightly
    // useful stacktrace in the log, though it's a python stacktrace
    // rather than a javascript one.
    exports.__esModule = true;
    module.exports = {
        ...require(javascript_dir),
        ...require("cumulusci"),
    };
} else {
    // this will show up in playwright-log.txt, alongside log.html
    console.info(`no javascript keyword folder found: ${javascript_dir}`);
}
