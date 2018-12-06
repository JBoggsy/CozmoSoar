# Cozmo Soar Proof-of-Concept

A proof-of-concept Doar debugger and interface for the Cozmo robot using the [Soar Markup
Language](https://soar.eecs.umich.edu/articles/articles/soar-markup-language-sml/78-sml-quick-start-guide) and the [Cozmo SDK](http://cozmosdk.anki.com/docs/index.html). The ultimate goal is
to have a mostly-functioning interactive Soar debugger which allows us to test writing Soar code 
for the embodied Cozmo robot.

## Soar-Cozmo Interface
We define the Soar-Cozmo interface to have the following input- and output-links which allow a 
Soar agent to interact with a Cozmo robot.

### Input-link
* battery_voltage (float)
* carrying_block [0|1]
* carrying_object_id (int)
* charging [0|1]
* cliff_detected (bool)
* face
  * expression (str)
  * expression_conf (int)
  * face_id (int)
  * name (str)
  * pose 
    * rot (float)
    * x (float)
    * y (float)
    * z (float)
* head_angle (float)
* lift
  * lift_angle (float)
  * lift_height (float)
  * lift_ratio (float)
* object
  * object_id (int)
  * connected [False|True]
  * cube_id (int)
  * descriptive_name (str)
  * moving [0|1]
  * liftable [0|1]
* face_count (int)
* obj_count (int)
* picked_up [0|1]
* pose 
  * rot (float)
  * x (float)
  * y (float)
  * z (float)
* robot_id (int)
* serial (str)

### Actions Overview
* display_face_image
  * duration (float)
  * screen_data (bytes)
* dock_with_cube
  * approach_angle (float)
  * target_object (int)
* drive_forward
  * distance (float)
  * speed (float)
* go_to_object
  * target_object_id (int)
  * distance (float)
* go_to_pose
  * pose
    * rot (float)
    * x (float)
    * y (float)
    * z (float)
  * relative_to_robot (bool)
* pick_up_object
  * object_id (int)
* place_object_down
* say_text
  * text (str)
  * duration_scale (float)
  * voice_pitch (float)
* set_backpack_lights
  * color (int)
* set_head_angle
  * angle (float)
  * accel (float)
  * max_speed (float)
  * duration (float)
* set_lift_height
  * height (float)
* stop_all_motors
* turn_in_place
  * angle (float)
  * speed (float)
  * accel (float)
  * angle_tolerance (float)
* turn_towards_face
  * face_id (int)
  
### Action Details
#### set-lift-height
*parameters:*
- height

Moves Cozmo's lift to the specified height. The height is given as a a float in the range [0, 1] that represents the percentage of the maximum height the lift should be moved to. A height value of 0.0 will move the lift all the way down while a value of 1.0 will move it all the way up. A value of 0.5 will move it exactly half-way up.

Presently this action is blocking, meaning the robot cannot do any other actions while this one is happening, and Soar won't continue until the action is compelete.

#### go-to-object
*parameters:*
- target_object_id
- distance

Instructs Cozmo to move itself to the object with the specified object ID. The object id must be one that Cozmo is currently aware of. The distance parameter tells Cozmo how close it should get to the object, in millimeters.

Presently this action is blocking, meaning the robot cannot do any other actions while this one is happening, and Soar won't continue until the action is compelete.