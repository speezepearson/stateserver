Start a server:
```bash
$ rm -rf /tmp/stateserver-test
$ mkdir /tmp/stateserver-test
$ python -m stateserver -p 24494 -d /tmp/stateserver-test
```
<!--
    >>> import subprocess, requests
    >>> _ = subprocess.check_call('mkdir -p /tmp/stateserver-test', shell=True)
    >>> _ = subprocess.check_call('rm /tmp/stateserver-test/*.json', shell=True)
    >>> server = subprocess.Popen('python -m stateserver -p 24494 -d /tmp/stateserver-test', shell=True)
    >>> import time; time.sleep(1)

-->

Now you can fetch state:
```python
>>> print(requests.get('http://localhost:24494/foo').text)
{"current_state": null}

```

Or write state:
```python
>>> print(requests.post('http://localhost:24494/foo', json={"old": None, "new": "hello"}).json())
{'success': True, 'current_state': 'hello'}

```

But writes only succeed if the old state matches up:
```python
>>> print(requests.post('http://localhost:24494/foo', json={"old": None, "new": "hello"}).json())
{'success': False, 'current_state': 'hello'}
>>> print(requests.post('http://localhost:24494/foo', json={"old": "hello", "new": "new state"}).json())
{'success': True, 'current_state': 'new state'}

```
