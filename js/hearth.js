import reset from 'reset-css';
import React, { Component } from 'react'
import ReactDOM from 'react-dom';
import ReconnectingWebsocket from 'reconnecting-websocket';
import { ThemeProvider, createMuiTheme } from '@mui/material/styles';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import BottomNavigation from '@mui/material/BottomNavigation';
import BottomNavigationAction from '@mui/material/BottomNavigationAction';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import FormLabel from '@mui/material/FormLabel';
import FormControl from '@mui/material/FormControl';
import FormGroup from '@mui/material/FormGroup';
import FormControlLabel from '@mui/material/FormControlLabel';
import FormHelperText from '@mui/material/FormHelperText';
import Icon from '@mui/material/Icon';
import BoltIcon from '@mui/icons-material/Bolt';
import HouseIcon from '@mui/icons-material/House';
import ListIcon from '@mui/icons-material/List';
import TextField from '@mui/material/TextField';
import IconButton from '@mui/material/IconButton';
import Switch from '@mui/material/Switch';
import Slider from '@mui/material/Slider';
import Tooltip from '@mui/material/Tooltip';
import Select from '@mui/material/Select';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import C3Chart from 'react-c3js';
import 'c3/c3.css';
import { go as fuzzysort } from 'fuzzysort';

const theme = createMuiTheme();

const DEVICES = {};
let HEARTH = null;

class QuickPane extends Component {
    render() {
        return "Quick"
    }
}

class HousePane extends Component {
    render() {
        const rooms = [...new Set(Object.keys(DEVICES).map(x => x.split('/')[0]))].sort()

        const rows = [];
        for (const room of rooms) {
            rows.push(
                <ListItem button key={room} onClick={(e,v)=>HEARTH.open_room(room)}>
                    <ListItemText primary={room} />
                </ListItem> );
        }
        return <List>{rows}</List>
    }
}

class DevicePane extends Component {
    constructor(props) {
        super(props)
        this.state = {filterText: props.defaultFilter}
    }
    update_filter(e) {
        this.setState({filterText: e.target.value});
    }

    render() {
        const devices = (this.state.filterText
            ? fuzzysort(this.state.filterText, Object.values(DEVICES), {key: 'id'}).map(x => x.obj)
            : Object.values(DEVICES)).sort((a,b) => (a.id < b.id ? -1 : (a.id > b.id ? 1 : 0)));
        return (<>
            <FilterHeader value={this.state.filterText} onChange={this.update_filter.bind(this)} />
            <DeviceList devices={devices} /></>
        )
    }
}

class Content extends Component {
    render() {
        switch (this.props.panel) {
            case "quick":
                return <QuickPane />
            break;
        case "house":
            return <HousePane />
            break
        case "devices":
            return <DevicePane defaultFilter={this.props.deviceFilter}/>
            break;
        }

        return null;
    }
}

class DeviceHandler {
    constructor(dev) {
        this.id = dev.id;
        this.props = dev
        this.component = null;
        this.state = dev.state;
        this.open = false;
    }

    openDialog() {
        this.open = true;
        HEARTH.forceUpdate();
    }
    closeDialog() {
        this.open = false;
        HEARTH.forceUpdate();
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
            HEARTH.forceUpdate();
        }
    }

    setComponent(component) {
        this.component = component;
    }

    send(payload) {
        payload.id = this.id;
        HEARTH.send(payload);
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

class FilterHeader extends Component {
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
                        value={this.props.value}
                        onChange={this.props.onChange}
                        fullWidth={true}
                    />
                </Toolbar></AppBar>
            </div>
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
                if (c.state) {
                    c.props.value = state[c.state];
                }
                return (
                    <Box>
                        <Typography>{c.props.label}</Typography>
                        <Slider
                            key={key}
                            onChange={(e,v) => action(v)}
                            valueLabelDisplay="on"
                            {...c.props} />
                    </Box>
                );
            case "Text":
                if (c.state) {
                    c.props.value = (c.state in state ? state[c.state] : "");
                    if (c.props.format) {
                        c.props.value = c.props.format.replace(/{(?::(\d+))?}/g, function(match, p1) { return (p1 ? c.props.value.toFixed(parseInt(p1, 10)) : c.props.value); });
                    }
                }
                return (
                    <table key={key} width="100%">
                        <tbody><tr><th align="left">
                            <Typography>{c.props.label}</Typography>
                        </th>
                        <td align="right">{c.props.value.toString()}</td></tr></tbody></table>
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
                fullscreen
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

class Hearth extends Component {
    constructor(props) {
        super(props)
        this.state = {active_panel: "quick", device_filter: null};
        this.ws = new ReconnectingWebsocket(
            'ws://' + window.location.hostname + ':' + window.location.port + '/ws',
        );
        this.ws.addEventListener('open', event => { this.sync_devices(); });
        this.ws.addEventListener('message', event => {
            this.handle_message(JSON.parse(event.data));
        });
        HEARTH = this;
    }

    handle_message(data) {
        if ('id' in data) {
            if (data['id'] === 0) {
                if ('m' in data && data['m'] == "devices") {
                    if ('devices' in data) {
                        const new_devices = {};
                        data.devices.forEach(dev => {
                            if (!(dev.id in DEVICES)) {
                                DEVICES[dev.id] = new DeviceHandler(dev);
                            }
                        });
                    }
                }
            } else if (data['id'] in DEVICES) {
                DEVICES[data['id']].handle_message(data)
            }
        }
    }

    open_room(room) {
        this.setState({active_panel: "devices", device_filter: room})
    }

    send(data) {
        this.ws.send(JSON.stringify(data))
    }

    sync_devices() {
        this.send({id: 0, m: "sync_devices", devices: []})
    }

    render() {
        return (
            <ThemeProvider theme={theme}>
                <Content panel={this.state.active_panel} deviceFilter={this.state.device_filter} />
                <Paper sx={{ position: 'fixed', bottom: 0, left: 0, right: 0 }} elevation={3}>
                    <BottomNavigation
                      showLabels
                      value={this.state.active_panel}
                      onChange={(event, newValue) => this.setState({active_panel: newValue })}>
                          <BottomNavigationAction label="Quick" value="quick" icon={<BoltIcon />} />
                          <BottomNavigationAction label="House" value="house" icon={<HouseIcon />} />
                          <BottomNavigationAction label="Devices" value="devices" icon={<ListIcon />} />
                  </BottomNavigation>
                </Paper>
            </ThemeProvider>
        );
    }
}

ReactDOM.render(<Hearth />, document.getElementById("app"))
