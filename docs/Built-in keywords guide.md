# Lireta keywords

This document explains the syntax of the built-in keywords of lireta, alongside some examples.

## `seq`

### Usage

```
seq [...]
```

Takes audio inputs, creates and returns a sequential audio.

### Examples

```
seq C D E F;
seq {seq C D E;} F;
```

Note that `note` is being called implicitily due to the note names.

## `note`

### Usage

```
note value [duration];
```

Reads from variables: `duration`, `octave`, `instrument`, `bpm`, `intensity`.

Takes a note name, creates and returns the corresponding audio. `duration` overrides the usage of the variable `duration`.

### Examples

```
note Eb 0.5;
```

## `simult`

### Usage

```
simult [...];
```

Takes audio inputs, creates and returns a simultaneous audio.

### Examples

```
simult C E G;
```
```
simult {
	seq C D E F G A B C+;
}{
	seq C- E- G-;
};
```

## `var`

### Usage

```
var name; # 1
var name = value; # 2
var name := value; # 3
```

(1) Acess and returns the value of the variable with the corresponding name.

(2) Assigns a value to the variable, and creates an error if it has not been declared yet. Search in parents scopes too.

(3) Declares a variable in the current scope and assigns a value.

### Examples
```
var x := 10;
var bpm = 100;
print {var x;};
```

## `print`

### Usage

```
print [...];
```

Prints strings.

### Examples

```
print "Hello World!";
print "bpm = " {var bpm;};
```

## `sfx`

### Usage

```
sfx name [duration];
```

Reads from variables: `duration`, `bpm`, `intensity`.

Creates and returns an audio sample with a pitchless instrument **without** changing the variable `instrument`. The parameters `duration` overrides the usage of the variable `duration`.

The instrument in the parameter must be a pitchless instrument.

### Examples

```
sfx bell;
```

## `repeat`

### Usage

```
repeat number [...];
```

Returns the block(s) repeated `number` times.

### Examples

```
repeat 50 C;
repeat 3 {
	seq A- B- C D;
};
```

## `func`

Usage:

```
func (!) f; # 1
func (!) f : ...; # 2
func (!) f = {...}; # 3
func (!) f := {...}; # 4
func (!) f : ... = {...}; # 5
func (!) f : ... := {...}; # 6
```

(1) Calls the function without any parameters.

(2) Calls the function with the informed parameters.

(3) Assigns a new parameterless function to an existing function.

(4) Declares a parameterless function.

(5) Assigns a new function (with parameters) to an existing function.

(6) Declares a function (with parameters).

The parameter `!` denotes that the function is "unclean", meaning it executes on the calling scope, not in the original one.

### Examples

Examples here will have comments explaining them due to the complexity of this keyword.

Parameters will be variable names, and they are separated by space:

```
func f : x y z = {
	{var x;};
};
```

Functions will automatically carry references to the variables in their parent scope:

```
func playm := {.;};
func setm := {.;};

{
	var m := D;
	func playm = {
		note {var m;};
	};
	func setm : x = {
		var m = {var x;};
	};
};

# now even if 'm' is inacessible directly,
func playm; # will play D;
func setm : C;
func playm; # will play C;
```

Similarly, functions that depend on variables outside their own scope can have their operation impacted by changes in those variables:

```
var t := 0;
func ! h : v := {
	note {var v;} {var t;}; # uses t=0
};
var t = 4; # now h uses t=4
```

It also can modify or read variables from the calling scope:

```
func f := {.;};

{
	# x was not even declared until now
	func ! f = {
		print {var x;};
	};
};

var x := 10;
func f; # will still be able to reach x=10
```

On the difference between clean and unclean functions, as mentioned before, unclean functions are executed in the calling scope, or more accuratelly, on a child of the calling scope, while clean functions are executed in a child of the declaring/assigning scope.

If a function needs to modify or read a variable that is not in the parameters but in the assigning scope, it should be a clean function, while if it operates closer to a macro, needing to modify or read from the calling scope, it should be a unclean function.

As the name suggest, avoid using unclean functions.

When a function could have mixed behaviour, an unclean wrapper that calls the clean and parts can be constructed:

```
func store := {.;};
func _setx := {.;};
func getx := {.;};

{
	var x := 0;

	func _setx : v = {
	    var x = {var v;};
	};

	func getx = {var x;};

	func ! store : u = {
        func _setx : {var {var u;};};
	};
};

# x remains unaccessible here

var k := 10;

func store_ptr : k; # sets x to the value of k
print {func getx;} "\n"; # access 10

var k = 5;

func store : k;
print {func getx;} "\n"; # access 5
```

## `.`

### Usage

```
. [...];
```

Executes the block(s) ignoring their return(s).

### Examples

```
. {func f;};

## `string`

## Usage

```
string [...];
```

Transforms parameters into strings, as long as they are compatible (for example, not audio, not functions), and concatenates if there are multiple parameters.

## Examples

```
string {func f;};
string whatever;
```
