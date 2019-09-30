test:
	pytest --doctest-glob=*.markdown --doctest-modules; \
	ps -ef \
	| grep 'python[ ]-m stateserver -p 24494 -d /tmp/stateserver-test' \
	| sed -e 's/^[a-zA-Z-]*  *\([0-9][0-9]*\).*/\1/' \
	| xargs --no-run-if-empty kill
