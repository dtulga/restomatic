
//
// HTML Compositor
//
// Library and reusable rendering functions for transforming data into
// HTML and performing asynchronous requests to JSON endpoints.
// Designed for use with the restomatic library, but can be adapted to
// other interfaces.
//
// WARNING: This software is in alpha, and API or function signatures may change before full release.
//

function updateHTMLRaw(element_id, html) {
    document.getElementById(element_id).innerHTML = html;
}

function updateText(element_id, text) {
    document.getElementById(element_id).textContent = text;
}

function updateHTMLCompositor(element_id, html_elements) {
    var html = '';
    if (Array.isArray(html_elements)) {
        html = html_elements.map(htmlCompositorGenerate).join('\n');
    } else {
        html = htmlCompositorGenerate(html_elements);
    }
    document.getElementById(element_id).innerHTML = html;
}

const escaped_fields = ['value', 'href', 'type', 'id', 'className', 'name', 'onclick', 'src', 'onmouseover', 'onblur', 'style'];
const present_fields = ['checked', 'selected'];
const unclosed_tags = ['input', 'br'];

function htmlCompositorGenerate(data) {
    if (typeof data !== 'object') {
        // Text nodes
        return escapeHTML(String(data));
    }
    var attributes = '';
    for (var i = 0; i < present_fields.length; i++) {
        const key = present_fields[i];
        if (data.hasOwnProperty(key) && data[key]) {
            attributes += ' ' + key;
        }
    }
    for (var i = 0; i < escaped_fields.length; i++) {
        const key = escaped_fields[i];
        const html_key = key == 'className' ? 'class' : key;
        if (data.hasOwnProperty(key)) {
            // Can have user data
            attributes += ' ' + html_key + '="' + escapeHTML(String(data[key])) + '"';
        }
    }
    var html = '<' + data['tag'] + attributes + '>';
    if (data.hasOwnProperty('innerHTML')) {
        // NO user data (unless previously escaped)
        html += data['innerHTML'];
    } else if (data.hasOwnProperty('innerText')) {
        // Can have user data
        html += escapeHTML(String(data['innerText']));
    } else if (data.hasOwnProperty('childElements')) {
        for (var i = 0; i < data['childElements'].length; i++) {
            html += htmlCompositorGenerate(data['childElements'][i]);
        }
    }
    if (!arrayIncludes(unclosed_tags, data['tag'])) {
        html += '</' + data['tag'] + '>';
    }
    return html;
}

function getClassList(element_id) {
    return document.getElementById(element_id).classList;
}

function formToJSON(form) {
    const elements = form.elements;
    var data = {};
    for (var i = 0; i < elements.length; i++) {
        if (!elements[i].name) {
            continue;
        }
        data[elements[i].name] = elements[i].type == "checkbox" ? elements[i].checked : elements[i].value;
    }
    return data;
}

function blanksToNullObj(obj) {
    for (var key in obj) {
        if (obj.hasOwnProperty(key) && obj[key] === '') {
            obj[key] = null;
        }
    }
    return obj;
}

function escapeHTML(msg) {
    var nu = "";
    var i = 0;
    while(i < msg.length) {
        const c = msg[i];
        if (c == '&' && msg[i+1] == '#') {
            // Don't double-escape
            var j = i + 2;
            if (msg[j] == 'x') {
                // Hex-style escapes
                j++;
            }
            var valid = false;
            while (j < msg.length) {
                const j_code = msg.charCodeAt(j);
                if (j_code >= 48 && j_code <= 57) {
                    j++;
                } else if (msg[j] == ';' && j > i + 2) {
                    valid = true;
                    break;
                } else {
                    // Not valid
                    break;
                }
            }
            if (valid) {
                // Skip this escaped sequence
                nu += msg.substring(i, j + 1);
                i = j + 1;
                continue;
            }
            // Otherwise escape as normal
        }
        const c_code = msg.charCodeAt(i);
        if (c_code <= 47 || (c_code >= 58 && c_code <= 64) || (c_code >= 91 && c_code <= 96) || c_code >= 123) {
            // Replace all special and unicode characters with html entites
            nu += "&#" + c_code + ";";
        } else {
            nu += c;
        }
        i++;
    }
    return nu;
}

function escapeJS(msg) {
    var nu = "";
    var i = 0;
    while(i < msg.length) {
        // Note no double-escape check here, as this style of escaping should never be returned from the server
        const c = msg[i];
        const c_code = msg.charCodeAt(i);
        if (c_code <= 47 || (c_code >= 58 && c_code <= 64) || (c_code >= 91 && c_code <= 96) || (c_code >= 123 && c_code < 256)) {
            // Replace all special (but not unicode) characters with JS escape sequences
            nu += "\\x" + c_code.toString(16);
        } else {
            nu += c;
        }
        i++;
    }
    return nu;
}

function historyPush(path, title) {
    if (window.location.pathname != path) {
        window.history.pushState({path: path}, title, path);
    }
}

const max_error_retries = 3;
const error_retry_delay_msec = 100;

function asyncJSONRequest(method, uri, callback, body, retry_count) {
    if (!retry_count) {
        retry_count = 0;
    }
    try {
        var req = new XMLHttpRequest();
        req.onreadystatechange = function() {
            if (this.readyState == 4) {
                if (this.status == 200 || this.status == 201) {
                    callback(JSON.parse(this.responseText));
                } else if (this.status >= 400 && this.status <= 599) {
                    displayError(JSON.parse(this.responseText)['message']);
                } else if (this.status != 0) {
                    displayError('Unknown response from server: ' + this.statusText);
                }
            }
        }
        req.open(method, uri, true);
        req.timeout = 5000;
        req.ontimeout = function (e) {
            displayError('Server connection timed out');
        }
        req.onerror = function (e) {
            if (retry_count < 0 || retry_count >= max_error_retries) {
                displayError('Server connection failed');
            } else {
                console.error('Detected error in connection, retrying');
                setTimeout(function() {
                    asyncJSONRequest(method, uri, callback, body, retry_count + 1);
                }, error_retry_delay_msec);
            }
        }
        if (body) {
            req.setRequestHeader('Content-Type', 'application/json');
            req.send(JSON.stringify(body));
        } else {
            req.send();
        }
    } catch (e) {
        displayError('Could not send request to server: ' + e);
    }
}

function asyncArrayBufferRequest(method, uri, callback, body, retry_count) {
    if (!retry_count) {
        retry_count = 0;
    }
    try {
        var req = new XMLHttpRequest();
        req.onreadystatechange = function() {
            if (this.readyState == 4) {
                if (this.status == 200 || this.status == 201) {
                    callback(this.response);
                } else if (this.status >= 400 && this.status <= 599) {
                    displayError(this.responseText);
                } else if (this.status != 0) {
                    displayError('Unknown response from server: ' + this.statusText);
                }
            }
        }
        req.open(method, uri, true);
        req.responseType = 'arraybuffer';
        req.timeout = 5000;
        req.ontimeout = function (e) {
            displayError('Server connection timed out');
        }
        req.onerror = function (e) {
            if (retry_count < 0 || retry_count >= max_error_retries) {
                displayError('Server connection failed');
            } else {
                console.error('Detected error in connection, retrying');
                setTimeout(function() {
                    asyncJSONRequest(method, uri, callback, body, retry_count + 1);
                }, error_retry_delay_msec);
            }
        }
        if (body) {
            req.setRequestHeader('Content-Type', 'application/json');
            req.send(JSON.stringify(body));
        } else {
            req.send();
        }
    } catch (e) {
        displayError('Could not send request to server: ' + e);
    }
}

function clearMessages() {
    updateText('message_bar', '');
}

function displayError(message) {
    clearMessages();
    updateHTMLCompositor('message_bar', {
        tag: 'div',
        className: "text_pad error",
        innerText: message
    });
}

function displaySuccess(message) {
    clearMessages();
    updateHTMLCompositor('message_bar', {
        tag: 'div',
        className: "text_pad success",
        innerText: message
    });
    // Clear after 30 seconds
    setTimeout(clearMessages, 30000);
}

function getNameUnit(name) {
    var name = name.replace(/_/g, ' ');
    var unit = '';
    if (name.substr(-3) == ' mm') {
        name = name.substr(0, name.length - 3);
        unit = ' mm';
    } else if (name.substr(-3) == ' ul') {
        name = name.substr(0, name.length - 3);
        unit = ' μL';
    }
    return [name, unit]
}

function detectColumnFormats(db_columns) {
    var formats = {};

    for (var i = 0; i < db_columns.length; i++) {
        const c_elements = db_columns[i].split(' ');
        const name = c_elements[0];
        const type = c_elements[1].toUpperCase();
        if (type == 'BOOLEAN') {
            formats[name] = 'boolean';
        }
    }

    return formats;
}

function generateJSONTableList(data_list, db_columns, display_names, postprocessor, blank_nulls) {
    if (blank_nulls !== false) {
        // Default to true
        blank_nulls = true;
    }

    const formats = detectColumnFormats(db_columns);

    var header_row = {tag: 'tr', childElements: []};
    for (var key in display_names) {
        header_row.childElements.push({tag: 'th', innerText: display_names[key]});
    }

    var table = {tag: 'table', className: 'display_table', childElements: [header_row]}

    for (var i = 0; i < data_list.length; i++) {
        const row = data_list[i];
        var table_row = {tag: 'tr', childElements: [{tag: 'a', id: 'row_' + row['id']}]};
        for (var key in row) {
            if (!display_names.hasOwnProperty(key)) {
                continue;  // Don't display hidden columns
            }
            var display_value = row[key];
            if (blank_nulls && (display_value === undefined || display_value === null)) {
                display_value = '';
            } else if (formats.hasOwnProperty(key) && formats[key] == 'boolean') {
                display_value = 'true' ? display_value > 0 : 'false';
            } else {
                display_value = String(display_value);
            }
            var td_cell = {tag: 'td', className: 'display_cell'};
            if (postprocessor) {
                display_value = postprocessor(row, key, display_value);
                if (!Array.isArray(display_value)) {
                    display_value = [display_value];
                }
                td_cell['childElements'] = display_value;
            } else {
                td_cell['innerText'] = display_value;
            }
            // TODO: Support units here?
            table_row.childElements.push(td_cell);
        }
        table.childElements.push(table_row);
    }

    return {tag: 'div', className: 'display_container', childElements: [table]};
}

// Note that this is limited to enum-like string values that have no internal single quotes
const check_constraint_regex = /\(?'([^']+)'\)?/;

function generateFormInputs(db_columns, display_names, edit_values) {
    var name_input_pairs = [];

    for (var i = 0; i < db_columns.length; i++) {
        const c = db_columns[i];

        if (c.indexOf("PRIMARY KEY") != -1) {
            // Do not display primary keys
            continue;
        }

        const c_elements = c.split(' ');
        var name = c_elements[0];
        if (arrayIncludes(['UNIQUE', 'CONSTRAINT'], name)) {
            continue;
        }
        const nu = getNameUnit(name);
        var display_name = nu[0];
        const unit = nu[1];

        if (display_names) {
            if (!display_names.hasOwnProperty(name)) {
                continue;  // Don't display hidden columns
            }
            display_name = display_names[name];
        }

        const type = c_elements[1].toUpperCase();
        var input = {tag: 'input', name: name};

        const current_value = edit_values && edit_values.hasOwnProperty(name) ? edit_values[name] : null;
        const set_current_value = current_value !== null;
        if (set_current_value) {
            input['value'] = current_value;
        }

        if (type == 'INTEGER' || type == 'REAL') {
            // A possible place of improvement would be to have more explicit ranges for these values
            input['type'] = 'number';
        } else if (type == 'BOOLEAN') {
            input['type'] = 'checkbox';
            if (set_current_value && current_value) {
                input['checked'] = true;
            }
            delete input['value'];
        } else if (type == 'TEXT') {
            if (c_elements.length > 5 && c_elements[2].toUpperCase() == 'CHECK' && c_elements[4].toUpperCase() == 'IN') {
                const allowed_entries = c_elements.slice(5).reduce(function(result, element) {
                    match = check_constraint_regex.exec(element);
                    if (match) {
                        const value = match[1];
                        var option = {
                            tag: 'option',
                            value: value,
                            innerText: value
                        };
                        if (current_value === value) {
                            option['selected'] = true;
                        }
                        result.push(option);
                    }
                    return result;
                }, []);
                input['tag'] = 'select';
                input['childElements'] = allowed_entries;
                delete input['value'];
            } else {
                input['type'] = "text";
            }
        } else {
            console.error('Unknown type: ' + type);
            continue;
        }
        if (unit.length > 0) {
            name_input_pairs.push([display_name, [input, unit]]);
        } else {
            name_input_pairs.push([display_name, [input]]);
        }
    }

    var table_rows = [];

    for (var i = 0; i < name_input_pairs.length; i++) {
        const ni = name_input_pairs[i];
        table_rows.push({
            tag: 'tr',
            childElements: [{
                tag: 'td',
                className: 'display_name',
                innerText: ni[0]
            }, {
                tag: 'td',
                childElements: ni[1]
            }]
        });
    }

    return {
        tag: 'div',
        className: 'form_container',
        childElements: [{
            tag: 'table',
            className: 'form_table',
            childElements: [{
                tag: 'tbody',
                childElements: table_rows
            }]
        }]
    };
}

function arrayIncludes(list, search) {
    return list.indexOf(search) >= 0;
}
