import reset from 'reset-css';
import React, { Component } from 'react'
import ReactDOM from 'react-dom';
import ReconnectingWebsocket from 'reconnecting-websocket';
import ExpansionPanel from '@material-ui/core/ExpansionPanel';
import ExpansionPanelSummary from '@material-ui/core/ExpansionPanelSummary';
import ExpansionPanelDetails from '@material-ui/core/ExpansionPanelDetails';
import { MuiThemeProvider, createMuiTheme } from '@material-ui/core/styles';
import AppBar from '@material-ui/core/AppBar';
import Toolbar from '@material-ui/core/Toolbar';
import List from '@material-ui/core/List';
import ListItem from '@material-ui/core/ListItem';
import ListItemText from '@material-ui/core/ListItemText';
import Button from '@material-ui/core/Button';
import Dialog from '@material-ui/core/Dialog';
import DialogActions from '@material-ui/core/DialogActions';
import DialogContent from '@material-ui/core/DialogContent';
import DialogContentText from '@material-ui/core/DialogContentText';
import DialogTitle from '@material-ui/core/DialogTitle';
import FormLabel from '@material-ui/core/FormLabel';
import FormControl from '@material-ui/core/FormControl';
import FormGroup from '@material-ui/core/FormGroup';
import FormControlLabel from '@material-ui/core/FormControlLabel';
import FormHelperText from '@material-ui/core/FormHelperText';
import Icon from '@material-ui/core/Icon';
import TextField from '@material-ui/core/TextField';
import IconButton from '@material-ui/core/IconButton';
import Switch from '@material-ui/core/Switch';
//import Slider from '@material-ui/core/Slider';
import Slider from 'rc-slider/lib/Slider';
import SliderHandle from 'rc-slider/lib/Handle';
import 'rc-slider/assets/index.css';
import Tooltip from '@material-ui/core/Tooltip';
import Select from '@material-ui/core/Select';
import InputLabel from '@material-ui/core/InputLabel';
import MenuItem from '@material-ui/core/MenuItem';
import C3Chart from 'react-c3js';
import 'c3/c3.css';
import { go as fuzzysort } from 'fuzzysort';

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
        this.component = null;
        this.state = dev.state;
        this.open = false;
    }

    openDialog() {
        this.open = true;
        this.hearth.forceUpdate();
    }
    closeDialog() {
        this.open = false;
        this.hearth.forceUpdate();
    }

    action(action) {
        action = action || 'set_single_state';
        let args = [].slice.call(arguments, 1)
        this.send({'m': action, args: args});
    }

    setState(state) {
        Object.assign(this.state, state);
        if (this.component) {
            this.component.setState(state);
            this.hearth.forceUpdate();
        }
    }

    setComponent(component) {
        this.component = component;
    }

    send(payload) {
        payload.id = this.id;
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
    componentWillMount() {
        this.handler = DEVICES[this.props.id];
        this.setState(this.handler.state);
    }

    componentDidMount() {
        this.handler.setComponent(this);
        //this.setState(this.handler.state);
    }

    componentWillUnmount() {
        this.handler.setComponent(null);
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
                return (
                    <FormControl>
                        <FormControlLabel
                            control={<Switch
                                key={key}
                                onChange={(e,v) => action(v)}
                                {...c.props} />}
                            label={c.props.label} />
                    </FormControl>
                );
            case "Slider":
                const tthandle = (props) => {
                  const { value, dragging, index, ...restProps } = props;
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
                    c.props.value = (c.state in state ? state[c.state] : "");
                    if (c.props.format) {
                        c.props.value = c.props.format.replace(/{(?::(\d+))?}/g, function(match, p1) { return (p1 ? c.props.value.toFixed(parseInt(p1, 10)) : c.props.value); });
                    }
                }
                return (
                    <table key={key} width="100%"><tbody><tr><th align="left">{c.props.label}</th><td align="right">{c.props.value.toString()}</td></tr></tbody></table>
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
                if (!("value" in c.props)) {
                    c.props.value = "";
                }
                return (
                    <FormControl>
                        <InputLabel>{c.props.label}</InputLabel>
                        <Select key={key} onChange={e => action(e.target.value)} {...c.props}>
                            {c.items.map(value => (<MenuItem value={value}>{value}</MenuItem>))}
                        </Select>
                    </FormControl>
                    );
        }
    }


    handleClose = () => { this.handler.closeDialog(); }

    render() {
        var dom = [];
        var components = this.props.ui.ui || [];
        for (let ci = 0; ci < components.length; ++ci) {
            let c = components[ci];
            let arg0 = c.arg0 || c.state || [];
            arg0 = Array.isArray(arg0) ? arg0 : [arg0];
            dom.push(this.UIComponent(c,
                                 this.state,
                                 "uic-" + this.props.id + "-" + ci,
                                 this.handler.action.bind(this.handler, c.action, ...arg0)));
            dom.push(<br />);
        }

        return (
            <Dialog
                key={'dialog-' + this.id}
                open
                onClose={this.handleClose.bind(this)}
            >
                <DialogTitle>{this.props.id}</DialogTitle>
                <DialogContent>
                    {dom}
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
        var dialog = "";

        for (var key in this.props.devices) {
            const device = this.props.devices[key];
            const id = String(device.id);

            rows.push(
                <ListItem button key={id} onClick={device.openDialog.bind(device)} >
                    {device.alerts("al" + id)}
                    <ListItemText primary={id} />
                </ListItem> );
            if (device.open) {
                dialog = <DeviceDialog {...device.props} />;
            }
        }

        return (
            <div>
                <List>
                    {rows}
                </List>
                {dialog}
            </div>
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
        const devices = (this.state.filterText
            ? fuzzysort(this.state.filterText, Object.values(this.state.devices), {key: 'id'}).map(x => x.obj)
            : Object.values(this.state.devices)).sort((a,b) => (a.id < b.id ? -1 : (a.id > b.id ? 1 : 0)));
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
