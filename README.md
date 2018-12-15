# Cozmo Soar Proof-of-Concept

A proof-of-concept Doar debugger and interface for the Cozmo robot using the [Soar Markup
Language](https://soar.eecs.umich.edu/articles/articles/soar-markup-language-sml/78-sml-quick-start-guide) and the [Cozmo SDK](http://cozmosdk.anki.com/docs/index.html). The ultimate goal is
to have a mostly-functioning interactive Soar debugger which allows us to test writing Soar code 
for the embodied Cozmo robot.

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
  * approach_angle (float)
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