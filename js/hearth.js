import reset from 'reset-css';
import React, { Component } from 'react'
import ReactDOM from 'react-dom';
import ReconnectingWebsocket from 'reconnecting-websocket';
import ExpansionPanel, {
  ExpansionPanelSummary,
  ExpansionPanelDetails,
} from 'material-ui/ExpansionPanel';
import { MuiThemeProvider, createMuiTheme } from 'material-ui/styles';
import AppBar from 'material-ui/AppBar';
import Toolbar from 'material-ui/Toolbar';
import List, {ListItem, ListItemText} from 'material-ui/List';
import Button from 'material-ui/Button';
import Dialog, {
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from 'material-ui/Dialog';
import {
  FormLabel,
  FormControl,
  FormGroup,
  FormControlLabel,
  FormHelperText,
} from 'material-ui/Form';
import Icon from 'material-ui/Icon';
import TextField from 'material-ui/TextField';
import IconButton from 'material-ui/IconButton';
import Switch from 'material-ui/Switch';
//import Slider from 'material-ui/Slider';
import Slider from 'rc-slider/lib/Slider';
import SliderHandle from 'rc-slider/lib/Handle';
import 'rc-slider/assets/index.css';
import Tooltip from 'material-ui/Tooltip';
import Select from 'material-ui/Select';
import { InputLabel } from 'material-ui/Input';
import { MenuItem } from 'material-ui/Menu';
import C3Chart from 'react-c3js';
import 'c3/c3.css';

const theme = createMuiTheme();

const DEVICES = {};

class Header extends Component {
    clear() {
		var input = document.getElementById('filter');
		input.value = "";
		this.props.onChange({target: input});
    }

    render() {
        return (
            <div id="header" style={{ height: '2cm' }}>
                <AppBar position="fixed"><Toolbar>
                    <IconButton onClick={this.clear.bind(this)}><Icon>close</Icon></IconButton>
                    <TextField
                        id="filter"
                        onChange={this.props.onChange}
                        fullWidth={true}
                    />
                </Toolbar></AppBar>
            </div>
        );
    }
}

class DeviceHandler {
    constructor(hearth, dev) {
        this.id = dev.id;
        this.hearth = hearth;
        this.props = dev
        this._statecb = null;
        this.state = dev.state;
    }

    action(action) {
        action = action || 'set_single_state';
        let args = [].slice.call(arguments, 1)
        this.send({'m': action, args: args});
    }

    setState(state) {
        if (this._statecb) {
            this._statecb(state);
        }
        this.hearth.forceUpdate();
        Object.assign(this.state, state);
    }

    setCallback(cb) {
        this._statecb = cb;
        if (this.state && cb) {
            cb(this.state);
        }
    }

    send(payload) {
        payload.id = this.id;
        console.log("Sending: ", payload);
        this.hearth.send(payload);
    }

    handle_message(data) {
        if ('state' in data) {
            console.log("Updating state: ", data['state']);
            this.setState(data['state']);
        }
    }

    alerts(key) {
        const res = [];
        if (this.state && this.state.alerts) {
            this.state.alerts.forEach(ainfo => {
                res.push(<Icon
                    key={key + ainfo.icon}
                    color={ainfo.color}
                    className="material-icons"
                    label={ainfo.label}>{ainfo.icon}</Icon>);
            });
        }
        return res;
    }
}

class DeviceDialog extends Component {
    constructor(props) {
        super(props);
        this.id = props.id;
        this.handler = DEVICES[props.id];
        this.state = this.handler.props.state;
        this.state.__open = false;
    }

    componentWillMount() {
        this.handler.setCallback(state => this.setState(state));
    }

    componentWillUnmount() {
        this.handler.setCallback(null);
    }

    UIComponent(c, state, key, action) {
        switch (c.class) {
            case "Button":
                c.props.children = c.props.label;
                return <Button
                    key={key}
                    onClick={(e) => action()}
                    {...c.props} />;
            case "Switch":
                if (c.state) {
                    c.props.checked = state[c.state];
                }
                return <FormControlLabel
                    control={<Switch
                    key={key}
                    onChange={(e,v) => action(v)}
                    {...c.props} />}
                    label={c.props.label} />;
            case "Slider":
                const tthandle = (props) => {
                  const { value, dragging, index, ...restProps } = props;
                  console.log(dragging);
                  return (
                    <Tooltip
                      title={value}
                      placement="top"
                      key={index}
                    >
                      <SliderHandle value={value} {...restProps} />
                    </Tooltip>
                  );
                };
                if (c.state) {
                    c.props.defaultValue = state[c.state];
                }
                return (
                    <div key={'div-' + key}>
                        <p>{c.props.label}</p>
                        <Slider
                            key={key}
                            handle={tthandle}
                            onAfterChange={action}
                            {...c.props} />
                    </div>
                );
            case "Text":
                if (c.state) {
                    if (c.props.format) {
                        c.props.value = c.props.format.replace(/{}/g, state[c.state]);
                    } else {
                        c.props.value = state[c.state];
                    }
                }
                return (
                    <table key={key} width="100%"><tbody><tr><th align="left">{c.props.label}</th><td align="right">{c.props.value}</td></tr></tbody></table>
                );
            case "C3Chart":
                if (c.state) {
                    c.props.data.json = state[c.state];
                }
                return (
                    <C3Chart
                        key={key}
                        {...c.props} />
                    );
            case "Select":
                if (c.state) {
                    c.props.value=state[c.state];
                }
                return (
                    <FormGroup>
                        <InputLabel>{c.props.label}</InputLabel>
                        <Select key={key} onChange={(e, i, v) => action(v)} {...c.props}>
                            {c.items.map(value => (<MenuItem value={value}>{value}</MenuItem>))}
                        </Select>
                    </FormGroup>
                    );
        }
    }


    handleOpen = () => { this.setState({__open: true}); }
    handleClose = () => { this.setState({__open: false}); }

    render() {
        var dom = [];
        var components = this.props.ui.ui || [];
        for (let ci = 0; ci < components.length; ++ci) {
            let c = components[ci];
            let arg0 = c.arg0 || c.state || [];
            arg0 = Array.isArray(arg0) ? arg0 : [arg0];
            dom.push(this.UIComponent(c,
                                 this.state,
                                 "uic-" + this.id + "-" + ci,
                                 this.handler.action.bind(this.handler, c.action, ...arg0)));
            //dom.push(<br />);
        }

        return (
            <Dialog
                key={'dialog-' + this.props.id}
                open={this.state.__open}
                onClose={this.handleClose.bind(this)}
            >
                <DialogTitle>{this.props.id}</DialogTitle>
                <DialogContent>
                    <FormControl fullWidth>
                        <FormGroup>
                            {dom}
                        </FormGroup>
                    </FormControl>
                    <DialogContentText>
                        {this.handler.alerts("ad" + this.props.id)}
                        (Last seen: {this.state.last_seen})
                    </DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button onClick={this.handleClose.bind(this)} >Close</Button>
                </DialogActions>
            </Dialog>
        );
    }
}

class DeviceList extends Component {
    render() {
        const rows = [];
        const dialogs = [];

        for (var key in this.props.devices) {
            const device = this.props.devices[key];
            const id = String(device.id);

            rows.push(
                <ListItem button key={id} onClick={device.setState.bind(device, {__open: true})} >
                    {device.alerts("al" + id)}
                    <ListItemText primary={id} />
                </ListItem> );
            dialogs.push(<DeviceDialog {...device.props} />);
        }

        return (
            <List>
                {rows}
                {dialogs}
            </List>
        );
    }
}

class Hearth extends Component {
    constructor(props) {
        super(props)
        this.state = {filterText: '', devices: {}};
        this.ws = new ReconnectingWebsocket(
            'ws://' + window.location.hostname + ':' + window.location.port + '/ws',
        );
        this.ws.addEventListener('open', event => { this.sync_devices(); });
        this.ws.addEventListener('message', event => {
            this.handle_message(JSON.parse(event.data));
        });
    }

    handle_message(data) {
        if ('id' in data) {
            if (data['id'] === 0) {
                if ('m' in data && data['m'] == "devices") {
                    if ('devices' in data) {
                        const new_devices = {};
                        data.devices.forEach(dev => {
                            if (!(dev.id in DEVICES)) {
                                DEVICES[dev.id] = new DeviceHandler(this, dev);
                            }
                        });
                        this.setState({devices: DEVICES});
                    }
                }
            } else if (data['id'] in DEVICES) {
                DEVICES[data['id']].handle_message(data)
            }
        }
    }

    send(data) {
        this.ws.send(JSON.stringify(data))
    }

    sync_devices() {
        this.send({id: 0, m: "sync_devices", devices: []})
    }

    update_filter(e) {
        this.setState({filterText: e.target.value});
    }

    render() {
        const devicenames = Object.keys(this.state.devices);
        const filterText = this.state.filterText.toLowerCase();
        const devices = Object.values(this.state.devices).filter(dev => String(dev.id).toLowerCase().indexOf(filterText) !== -1);
        devices.sort((a,b) => String(a.id).localeCompare(String(b.id)));
        return (
            <MuiThemeProvider theme={theme}>
                <div>
                    <Header onChange={this.update_filter.bind(this)} />
                    <DeviceList devices={devices} />
                </div>
            </MuiThemeProvider>
        );
    }
}

ReactDOM.render(<Hearth />, document.getElementById("app"))
