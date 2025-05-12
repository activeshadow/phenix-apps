# record Component

Starts and stops VNC screen recording on specified hosts.

```
type: record
exe: phenix-scorch-component-record
```

## Metadata Options

```yaml
metadata:
  vms:
    - hostname:
        configure:
          - action: <start / stop> # starts or stops VNC recording on specified host
            filename: <custom-filename.fb / hostname_timestamp.fb > # If left blank, filename defaults to <VM hostname>_<timestamp>.fb
        start: [] # same array of keys as above
        stop: [] # same array of keys as above
        cleanup: [] # same array of keys as above
```
Component output can be located in Experiment > Files > \<filename\>.fb in the phenix GUI

## Example Configuration

```yaml
- name: test-record
  type: record
  metadata: 
    vms:
      - hostname: my-vm
      start:
          - action: start 
            filename: my-file.fb
      stop:
          - action: stop
```