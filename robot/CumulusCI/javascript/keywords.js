var cci = require("cumulusci");

async function get_cci_context() {
    return cci;
}

exports.__esModule = true;
module.exports = {
    get_cci_context,
};
