# Cozmo-Soar Interface

A python-based interface between the [Soar Cognitive Architecture](https://soar.eecs.umich.edu/) and the [Cozmo](https://www.anki.com/en-us/cozmo) robot by Anki. The [Soar Markup
Language](https://soar.eecs.umich.edu/articles/articles/soar-markup-language-sml/78-sml-quick-start-guide), Aaron Mininger's [PySoarLib](https://github.com/amininger/pysoarlib) and the [Cozmo SDK](http://cozmosdk.anki.com/docs/index.html) are used to build this interface. The purpose of the interface is to allow a Soar agent to control a fully-embodied Cozmo robot, thereby embodying the Soar agent in the real world and enabling cognitive experiments to be run on a small, flexible, and robust platform.

## Installation
Several libraries and tools are needed prior to installing the Cozmo-Soar interface itself.

1. Install both [Python 2.7.11](https://www.python.org/downloads/release/python-2713/) or above, and [Python 3.6](https://www.python.org/downloads/) or above. 
    1. I also recommend creating and using a Python3.6+ virtual environment with the [virtualenv](https://virtualenv.pypa.io/en/latest/) tool. If you do this, use the python interpreter in this virtual environment for every python call except where specifically noted.
    2. Make a note of the path to the Python 3 installation. You will need to use the path to the Python 3 binary later.
2. Download and build the Soar Cognitive Architecture.
    1. Download the source code from GitHub [here](https://github.com/SoarGroup/Soar).
    2. Install the necessary prerequisites to Soar. The prerequrisites for each OS are listed in different pages [here](https://soar.eecs.umich.edu/articles/articles/building-soar).
    3. In Windows, open the Visual Studio Command Prompt; in Liinux or Mac, open the terminal. Then, cd into the root directory of the Soar source code.
    4. In Windows, run the command `build all --python=[Python3 path]`, while in Linux or Mac, run `python scons/scons.py all --python=[Python3 path]`, filling in the path to your Python 3 executable from step 1. *The python executable used to run this command in Linux or Mac must be Python 2.7.11+, NOT Python 3*. 
    5. Add the `out/` directory generated to your system's `PYTHONPATH` environmental variable.
3. Use pip to install the following python libraries to your Python 3.6 installation:
    1. `pillow`
    2. `cozmo`
    3. `opencv-python`
4. Create a new directory, and download Aaron Mininger's `PySoarLib` (linked above) from GitHub to that folder, and add the new directory, which should contain the root directory of `PySoarLib`, to your `PYTHONPATH`.
5. Finally, download the Cozmo-Soar Interface code from GitHub, and add its root directory to your `PYTHONPATH`.

## How to Use
To run a Soar agent using this interface, simply `cd` to the directory holding `main.py` and run 

```
python3 main.py [path/to/agent.soar]
```
replacing `[path/to/agent.soar]` appropriately. This will run the Soar agent in continuous run 
mode. adding the `-i` flag will instead run in interactive mode, which allows you to send Soar 
commands. In order to advance the agent in this mode, use the `step` command. 

## Cozmo-Soar Interface
The Cozmo-Soar interface provides certain input-link attributes and values to a Soar agent, and listens for certain output-link attributes and their values to allow the agent to control the Cozmo. The nature of these are described below: 

### Input-link Overview
* [battery-voltage](#battery-voltage) (float)
* [carrying-block](#carrying-block) (int)
* [carrying-object-id](#carrying-object-id) (int)
* [charging](#charging) (int)
* [cliff-detected](#cliff-detected) (int)
* [face](#face)
  * expression (str)
  * expression-conf (int)
  * face-id (int)
  * name (str)
  * pose 
    * rot (float)
    * x (float)
    * y (float)
    * z (float)
* [face-count](#face-count) (int)
* [head-angle](#head-angle) (float)
* [lift](#lift)
  * angle (float)
  * height (float)
  * ratio (float)
* [object](#object)
  * object-id (int)
  * connected (str)
  * cube-id (int)
  * descriptive_name (str)
  * moving (str)
  * liftable (int)
  * type (str)
  * pose
    * rot (float)
    * x (float)
    * y (float)
    * z (float)
* [obj-count](#obj-count) (int)
* [picked-up](#picked-up) (int)
* [pose](#pose) 
  * rot (float)
  * x (float)
  * y (float)
  * z (float)
* [robot-id](#robot-id) (int)
* [serial](#serial) (str)

### Actions Overview
* [dock-with-cube](#dock-with-cube)
  * object-id (int)
* [drive-forward](#drive-forward)
  * distance (float)
  * speed (float)
* [go-to-object](#go-to-object)
  * object-id (int)
* [move-head](#move-head)
  * angle (float)
* [move-lift](#move-lift)
  * height (float)
* [pick-up-object](#pick-up-object)
  * object-id (int)
* [place-object-down](#place-object-down)
* [set-backpack-lights](#set-backpack-lights)
  * color (str)
* [turn-in-place](#turn-in-place)
  * angle (float)
  * speed (float)
* [turn-to-face](#turn-to-face)
  * face-id (int)
  
### Input Details
I've enumerated the different inputs a Soar agent receives from Cozmo and their meanings and potential values. Additionally, each is linked to their corresponding entry in Cozmo's SDK documentation, which may give more information.
#### [battery-voltage](http://cozmosdk.anki.com/docs/generated/cozmo.robot.html#cozmo.robot.Robot.battery_voltage)
A float. The current battery voltage. According to Cozmo's documentation, a voltage less than 3.5 is considered low.

#### [carrying-block](http://cozmosdk.anki.com/docs/generated/cozmo.robot.html#cozmo.robot.Robot.is_carrying_block)
An integer, either 0 for false or 1 for true. Indicates whether Cozmo is carrying a block.

#### [carrying-object-id](http://cozmosdk.anki.com/docs/generated/cozmo.robot.html#cozmo.robot.Robot.carrying_object_id)
An integer. The object id of the object which Cozmo is carrying. 

#### [charging](http://cozmosdk.anki.com/docs/generated/cozmo.robot.html#cozmo.robot.Robot.is_charging)
An integer, either 0 for false or 1 for true. Indicates if Cozmo is currently being charged.

#### [cliff-detected](http://cozmosdk.anki.com/docs/generated/cozmo.robot.html#cozmo.robot.Robot.is_cliff_detected)
An integer, either 0 for false or 1 for true. Indicates if Cozmo has detected a cliff in front of it. 

#### [face](http://cozmosdk.anki.com/docs/generated/cozmo.faces.html#cozmo.faces.Face)
Provides information about a face Cozmo can currently see, such as its pose, expression, and name. Each face Cozmo sees corresponds to a unique ^face augmentation to the input-link. Face augmentations provide the following information:
* `expression`: A string indicating what expression Cozmo thinks the face is displaying. Possiblities include "happy", "angry", "sad", and "neutral". 
* `exp-score`: An integer indicating Cozmo's confidence in its expression assignment. Maximum score is 100.
* `face-id`: An integer ID given to the face internally, which uniquely identifies it among those seen. Note that this is not guaranteed to remain the same if the face leaves Cozmo's vision and then returns.
* `name`: The name Cozmo associates with the face, if it has one.
* `pose`: Pose information about the head. See [pose](#pose) 

#### [head-angle](http://cozmosdk.anki.com/docs/generated/cozmo.robot.html#cozmo.robot.Robot.head_angle)
A float in [-25.00, 44.50]. Indicates the angle of Cozmo's head in degrees, where 0 is looking directly forward. The bounds of the range are the minimum and maximum head angle Cozmo can achieve.

#### [lift](http://cozmosdk.anki.com/docs/generated/cozmo.util.html#cozmo.util.Pose)
The lift augmentation to the input-link provides information about the location of the lift in several forms:
* `angle`: A float in [-11.36, 45.41]. The angle of Cozmo's lift relative to the ground in degrees. 
* `height`: A float in [32.00, 92.00]. The height of the lift off the ground in millimeters.
* `ratio`: A float in [0.0, 1.0]. The ratio between how high the lift currently is and its maximum height. So a value of 0.0 means the lift is as low as possible, and a value of 1.0 is as high as possible.

#### [object](http://cozmosdk.anki.com/docs/generated/cozmo.objects.html#cozmo.objects.ObservableObject)
Provides information about an object Cozmo can currently see and recognize, such as its pose information, whether it can be lifted, and an ID for it. Each object augmentation corresponds to a unique object Cozmo can see, and can provide some or all of the following information:
* `connected`: An string, either 'False' or 'True'. Indicates whether the object is connected to Cozmo via Bluetooth. Only given for Light Cube objects.
* `cube-id`: An integer in [1, 3] which uniquely identifies which image is on the Light Cube. The paperclip with a lightning bolt is 1, the angled square with a curved tail is 2, and the one with a small square connected to a larger square is 3. Only provided if the object is a Light Cube.
* `descriptive-name`: A descriptive string name given to the object.
* `liftable`: An integer, either 0 for false or 1 for true. Indicates whether Cozmo can pick up the object with its lift.
* `moving`: A string either "False" or "True". Indicates whether the object is moving based on its accelerometer. Only provided if the object is a Light Cube.
* `object-id`: An integer uniquely identifying the object among all those Cozmo can currently see. Note that the ID of an object may not be the same if it leaves and then reenters Cozmo's vision.
* `type`: A string indicating what kind of object it is. Normally "object", but will be "cube" if the object is a Light Cube.
* `pose`: Pose information about the object. See [pose](#pose).

#### [face-count](http://cozmosdk.anki.com/docs/generated/cozmo.world.html#cozmo.world.World.visible_face_count)
An integer. Indicates how many faces Cozmo currently sees.

#### [obj-count](http://cozmosdk.anki.com/docs/generated/cozmo.world.html#cozmo.world.World.visible_objects)
An integer. Indicates how many objects Cozmo currently sees.

#### [picked-up](http://cozmosdk.anki.com/docs/generated/cozmo.robot.html#cozmo.robot.Robot.is_picked_up)
An integer, either 0 for false or 1 for true. Indicates whether Cozmo thinks it's been picked up off a surface.

#### [pose](http://cozmosdk.anki.com/docs/generated/cozmo.util.html#cozmo.util.Pose)
Provides information about the location and orientation of Cozmo, objects, and faces. Pose values are calculated by Cozmo relative to where Cozmo is on start-up, and the rotation is relative to Cozmo's initial heading. However, if Cozmo is de-localized, all existing pose information is invalidated, and a new origin is generated. Pose information includes:
* `x`: A float indicating the distance in millimeters between the origin and Cozmo (or the object/face) on the x axis.
* `y`: A float indicating the distance in millimeters between the origin and Cozmo (or the object/face) on the y axis.
* `z`: A float indicating the distance in millimeters between the origin and Cozmo (or the object/face) on the z axis.
* `rot`: The heading of Cozmo (or the object/face) in degrees. 

#### [robot-id](http://cozmosdk.anki.com/docs/generated/cozmo.robot.html#cozmo.robot.Robot.robot_id)
An integer. The internal id number of the robot.

#### [serial](http://cozmosdk.anki.com/docs/generated/cozmo.robot.html#cozmo.robot.Robot.serial)
An string. The serial number of the robot in hex.

### Action Details

#### [move-lift](http://cozmosdk.anki.com/docs/generated/cozmo.robot.html#cozmo.robot.Robot.set_lift_height)
*parameters:*
- `height`: `float`

Moves Cozmo's lift to the specified height. The height is given as a a float in the range [0, 1] that represents the percentage of the maximum height the lift should be moved to. A height value of 0.0 will move the lift all the way down while a value of 1.0 will move it all the way up. A value of 0.5 will move it exactly half-way up.

#### [go-to-object](http://cozmosdk.anki.com/docs/generated/cozmo.robot.html#cozmo.robot.Robot.go_to_object)
*parameters:*
- `object-id`: `int`

Instructs Cozmo to move itself to the object with the specified object ID. The object id must be one that Cozmo can currently see. Cozmo will stop once its center is 100mm from the object's.

#### [set-backpack-lights](http://cozmosdk.anki.com/docs/generated/cozmo.robot.html#cozmo.robot.Robot.set_all_backpack_lights)
*parameters:*
- `color`: `str`

Changes the color of the lights on Cozmo's back. The lights can be set to either "red", "green", "blue", or "white", or "off".

#### [drive-forward](http://cozmosdk.anki.com/docs/generated/cozmo.robot.html#cozmo.robot.Robot.drive_straight)
*parameters:*
- `distance`: `float`
- `speed`: `float`

Instructs Cozmo to drive forward the given distance at the given speed. The distance is given in mm and the speed in mm/s. 

#### [turn-in-place](http://cozmosdk.anki.com/docs/generated/cozmo.robot.html#cozmo.robot.Robot.turn_in_place)
*parameters:*
- `angle`: `float`
- `speed`: `float`

Instructs Cozmo to rotate in place, turning `angle` degrees at `speed` degrees a second. A positive value for `angle` rotates Cozmo counterclockwise, a negative value rotates clockwise.

#### [pick-up-object](http://cozmosdk.anki.com/docs/generated/cozmo.robot.html#cozmo.robot.Robot.pickup_object)
*parameters:*
- `object-id`: `int`

Instructs Cozmo to attempt to lift the specified object. The object must be known beforehand, and must be liftable. Cozmo will do its best to autonomously approach the object, get its lift hooks under the right spot, and the raise the lift. This is not super reliable, however, and is prone to failing a few times before Cozmo gets it right.

#### [place-object-down](http://cozmosdk.anki.com/docs/generated/cozmo.robot.html#cozmo.robot.Robot.place_object_on_ground_here)
*parameters:*

Instructs Cozmo to lower whatever object it is carrying to the ground, then back up. No object id is required, since this action is really equivalent to instructing Cozmo to fully lower its lift and then back up a tad.

#### [place-object-on](http://cozmosdk.anki.com/docs/generated/cozmo.robot.html#cozmo.robot.Robot.place_on_object)
*parameters:*
- `object-id`: `int`

Instructs Cozmo to place the block its currently carrying on top of the specified object.
   
#### [dock-with-cube](http://cozmosdk.anki.com/docs/generated/cozmo.robot.html#cozmo.robot.Robot.dock_with_cube)
*parameters:*
- `object-id`: `int` 

Instructs Cozmo to approach a cube and dock with it, so that the lift hooks are under the grip holes and if the lift were to move up, the cube would be lifted. The specified object must be liftable, and preferably a light cube.

#### [move-head](http://cozmosdk.anki.com/docs/generated/cozmo.robot.html#cozmo.robot.Robot.set_head_angle)
*parameters:*
- `angle`: `float`

Intstructs Cozmo to move its head to the specified angle, where the angle is in degrees and relative to looking straight ahead. The angle should be in the range  [-0.44, 0.78], where -0.44 is looking as far down as possible, and 0.78 is looking as far up as possible.

## Future Work
* Currently, if the agent sends a command to the Cozmo, the Soar cycle pauses until the Cozmo is completely done with the action. It'd be nice if Soar could continue to run while Cozmo is executing an action.
*  Create a GUI which display Soar state information (e.g., state, input-link, output-link), Cozmo information (including the camera view), and the ability to give Soar new commands.