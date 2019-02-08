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
4. Download Aaron Mininger's PySoarLib (linked above) from GitHub, and add the root directory to your `PYTHONPATH`.
5. Finally, download the Cozmo-Soar Interface code from GitHub, and add its root directory to your `PYTHONPATH`.

## Soar-Cozmo Interface
We define the Soar-Cozmo interface to have the following input- and output-links which allow a 
Soar agent to interact with a Cozmo robot. 

### Input-link
* battery-voltage (float)
* carrying-block [0|1]
* carrying-object_id (int)
* charging [0|1]
* cliff-detected (bool)
* face
  * expression (str)
  * expression-conf (int)
  * face-id (int)
  * name (str)
  * pose 
    * rot (float)
    * x (float)
    * y (float)
    * z (float)
* head-angle (float)
* lift
  * lift-angle (float)
  * lift-height (float)
  * lift-ratio (float)
* object
  * object-id (int)
  * connected [False|True]
  * cube-id (int)
  * descriptive_name (str)
  * moving [0|1]
  * liftable [0|1]
* face-count (int)
* obj-count (int)
* picked-up [0|1]
* pose 
  * rot (float)
  * x (float)
  * y (float)
  * z (float)
* robot-id (int)
* serial (str)

### Actions Overview
* dock-with-cube
  * target_object (int)
* drive-forward
  * distance (float)
  * speed (float)
* go-to-object
  * target_object_id (int)
  * distance (float)
* go-to-pose
  * pose
    * rot (float)
    * x (float)
    * y (float)
    * z (float)
  * relative_to_robot (bool)
* pick-up-object
  * object_id (int)
* place-object-down
* say-text
  * text (str)
  * duration_scale (float)
  * voice_pitch (float)
* set-backpack-lights
  * color (int)
* set-head-angle
  * angle (float)
  * accel (float)
  * max_speed (float)
  * duration (float)
* set-lift-height
  * height (float)
* stop-all-motors
* turn-in-place
  * angle (float)
  * speed (float)
  * accel (float)
  * angle_tolerance (float)
* turn-to-face
  * face_id (int)
  
### Action Details

#### set-lift-height
*parameters:*
- height

Moves Cozmo's lift to the specified height. The height is given as a a float in the range [0, 1] that represents the percentage of the maximum height the lift should be moved to. A height value of 0.0 will move the lift all the way down while a value of 1.0 will move it all the way up. A value of 0.5 will move it exactly half-way up.

Presently this action is blocking, meaning the robot cannot do any other actions while this one is happening.

#### go-to-object
*parameters:*
- target-object-id

Instructs Cozmo to move itself to the object with the specified object ID. The object id must be one that Cozmo is currently aware of. Cozmo will stop once its center is 150mm from the object's.

Presently this action is blocking, meaning the robot cannot do any other actions while this one is happening.

#### turn-to-face
*parameters:*
- face-id 

Instructs Cozmo to rotate towards a face it sees. The face id should be one it knows about.

#### set-backpack-lights
*parameters:*
- color

Changes the color of the lights on Cozmo's back. The lights can be set to either red, green, 
blue, or white, or be turned off.

#### drive-forward
*parameters:*
- distance
- speed

Instructs Cozmo to drive forward the given distance at the given speed. The distance is given in 
mm and the speed in mm/s. 

#### turn-in-place
*parameters:*
- angle
- speed

Instructs Cozmo to rotate in place, turning `angle` degrees at `speed` degrees a second. A positive value for `angle` rotates Cozmo counterclockwise, a negative value rotates clockwise.

#### pick-up-object
*parameters:*
- object_id

Instructs Cozmo to attempt to lift the specified object. The object must be known beforehand, and must be liftable. Cozmo will do its best to autonomously approach the object, get its lift hooks under the right spot, and the raise the lift. This is not super reliable, however, and is prone to failing a few times before Cozmo gets it right.

#### place-object-down
*parameters:*

Instructs Cozmo to lower whatever object it is carrying to the ground, then back up. No object id is required, since this action is really equivalent to instructing Cozmo to fully lower its lift and then back up a tad.

#### place-object-on
*parameters:*
- target_object_id

Instructs Cozmo to place the block its currently carrying on top of the specified object.
   
#### dock-with-cube
*parameters:*
- object_id

Instructs Cozmo to approach a cube and dock with it, so that the lift hooks are under the grip holes and if the lift were to move up, the cube would be lifted. The specified object must be liftable, and preferably a light cube.