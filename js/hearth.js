import React, { Component } from 'react'
import ReconnectingWebsocket from 'reconnecting-websocket';
import MuiThemeProvider from 'material-ui/styles/MuiThemeProvider';
import AppBar from 'material-ui/AppBar';
import {List, ListItem} from 'material-ui/List';
import FlatButton from 'material-ui/FlatButton';
import Dialog from 'material-ui/Dialog';
import FontIcon from 'material-ui/FontIcon';
import Subheader from 'material-ui/Subheader';
import TextField from 'material-ui/TextField';
import IconButton from 'material-ui/IconButton';
import NavigationClose from 'material-ui/svg-icons/navigation/close';
import Toggle from 'material-ui/Toggle';
import Slider from 'material-ui/Slider';
import C3Chart from 'react-c3js';
import 'c3/c3.css';

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
                <AppBar style={{ position: 'fixed' }}
					iconElementLeft={<IconButton onClick={this.clear.bind(this)}><NavigationClose /></IconButton>}
					title={
						<TextField
							id="filter"
							onChange={this.props.onChange}
							fullWidth={true}
						/>}
				/>
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
        if (this.state) {
            cb(this.state);
        }
    }

    uiclass() {
        switch(this.props.ui.class) {
            default:
                return <Device {...this.props} />
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
                res.push(<FontIcon
                    key={key + ainfo.icon}
                    color={ainfo.color}
                    className="material-icons"
                    label={ainfo.label}>{ainfo.icon}</FontIcon>);
            });
        }
        return res;
    }
}

class Device extends Component {
    constructor(props) {
        super(props);
        this.id = props.id;
        this.handler = DEVICES[props.id];
        this.handler.setCallback(state => this.setState(state));
        this.state = this.handler.props.state;
        this.state.__open = false;
    }

    UIComponent(c, state, key, action) {
        switch (c.class) {
            case "FlatButton":
                return <FlatButton key={key} onClick={(e) => action()} {...c.props} />;
            case "Toggle":
                if (c.state) {
                    c.props.toggled = state[c.state];
                }
                return <Toggle key={key} onToggle={(e,v) => action(v)} {...c.props} />;
            case "Slider":
                if (c.state) {
                    c.props.value = state[c.state];
                }
                return (
                    <div key={'div-' + key}>
                        <Subheader>{c.props.label}</Subheader>
                        <Slider
                            key={key}
                            onChange={(e,v) => {this.value = v}}
                            onDragStop={(e) => {action(this.value)}}
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
                    <C3Chart key={key} {...c.props} />
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
        }

        const actions = [
            <FlatButton
                label="Close"
                keyboardFocused={true}
                onClick={this.handleClose.bind(this)}
            />
            ];

        return (
            <Dialog
                title={this.props.id}
                actions={actions}
                open={this.state.__open}
                onRequestClose={this.handleClose}
                modal={false}
            >
                {dom}
                <div>
                    {this.handler.alerts("ad" + this.props.id)}
                    (Last seen: {this.state.last_seen})
                </div>
            </Dialog>
        );
    }
}

class DeviceList extends Component {
    render() {
        const rows = [];
        const all_bins = [];
        let last_id = null;

        for (var key in this.props.devices) {
            const device = this.props.devices[key];
            const id = String(device.id);

            let extras = {};
            //if (device.props.ui.rightIcon) {
                //let icon = device.props.ui.rightIcon;
                //let raction = device.props.ui.rightAction;
                //raction = raction ? device.action.bind(device, raction) : null;
                //extras.rightIcon = (<IconButton
                    //iconClassName="material-icons"
                    //onClick={device.action.bind(device, raction)}> {icon} </IconButton>);
            //}
            //console.log("Extras: ", id, extras, device.props.ui);
            const ptext = (
                <div>
                    {device.alerts("al" + device.id)}
                    {id}
                </div>
            );
            rows.push(<ListItem
                primaryText={ptext}
                key={id}
                onClick={device.setState.bind(device, {__open: true})}
                {...extras}
            >{device.uiclass()}</ListItem> );
        }

        return (
            <List>
                {rows}
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
        const devices = Object.values(this.state.devices).filter(dev => String(dev.id).indexOf(this.state.filterText) !== -1);
        devices.sort((a,b) => String(a.id).localeCompare(String(b.id)));
        return (
            <MuiThemeProvider>
                <div>
                    <Header onChange={this.update_filter.bind(this)} />
                    <DeviceList devices={devices} />
                </div>
            </MuiThemeProvider>
        );
    }
}

ReactDOM.render(<Hearth />, document.getElementById("app"))
