# Lireta keywords
## `seq`
Usage:

```
seq [...]
```

Takes audio inputs, creates and returns a sequential audio.

## `note`
Usage:

```
note value [duration]
```

Uses variables: `duration`, `octave`, `instrument`, `bpm`, `intensity`.

Takes a note name, creates and returns the corresponding audio. `duration` overrides the usage of the variable `duration`.

## `simult`

Usage:

```
simult [...]
```

Takes audio inputs, creates and returns a simultaneous audio.

## `var`

Usage:

```
var name (1)
var name = value (2)
var name := value (3)
```

(1) Acess and returns the value of the variable with the corresponding name.

(2) Assigns a value to the variable, and creates an error if it has not been declared yet. Search in parents scopes too.

(3) Declares a variable in the current scope and assigns a value.

## `print`

Usage:

```
print [...]
```

Prints strings.

## `sfx`

Usage:

```
sfx name [duration]
```

Uses variables: `duration`, `bpm`.

Creates and returns an audio sample with a pitchless instrument without changing the variable `instrument`. `duration` overrides the usage of the variable `duration`.


## `repeat`

Usage:
```
repeat number [...]
```

Returns the block(s) repeated `number` times.


## `func`

Usage:

```
func f (1)
func f : ... (2)
func f = {...} (3)
func f := {...} (4)
func f : ... = {...} (5)
func f : ... := {...} (6)
```

(1) Calls the function without any parameters.

(2) Calls the function with the informed parameters.

(3) Assigns a new parameterless function to an existing function.

(4) Declares a parameterless function.

(5) Assigns a new function (with parameters) to an existing function.

(6) Declares a function (with parameters).

Parameters are strings that will be variable names, separated by space, like
```
func f : x y z = { {var x;}; };
```

Functions will automatically carry references to the variables in their parent scope, so something like
```
# suppose g already exists
{
	var m := D;
	func g = {note {var m;}; };
};

func g; # will be equivalent to note D, even if m is not accessible in this scope.
```

Similarly, functions that depend on variables outside their own scope can have their operation impacted by changes in those variables, such as in
```
var t := 0;
func h : v := { note {var v;} {var t;}; }; # uses t=0
var t = 4; # now h sees t=4
```

## `.`

Usage:
```
. [...]
```
Executes the block(s) ignoring their return(s).
