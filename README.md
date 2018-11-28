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
* carrying_block (bool)
* carrying_object
  * descriptive_name (str)
  * object_id (int)
  * object_type (str)
* charging (bool)
* cliff_detected (bool)
* face_detected_n
  * expression (str)
  * expression_conf (int)
  * face_id (int)
  * name (str)
* head_angle (float)
* lift
  * lift_angle (float)
  * lift_height (float)
  * lift_ratio (float)
* light_cube_n
  * connected (bool)
  * cube_id (int)
  * descriptive_name (str)
  * moving (bool)
* face_count (int)
* obj_count (int)
* picked_up (bool)
* pose 
  * rot (float)
  * x (float)
  * y (float)
  * z (float)
* robot_id (int)

### Output-link.action
* abort-action
  * completed (bool)
* display_face_image
  * completed (bool)
  * duration (float)
  * screen_data (bytes)
  * parallel (bool)
* dock_with_cube
  * completed (bool)
  * approach_angle (float)
  * parallel (bool)
  * target_object (int)
* drive_forward
  * completed (bool)
  * distance (float)
  * speed (float)
  * parallel (bool)
* go_to_object
  * completed (bool)
  * target_object (int)
  * distance_from_object (float)
  * parallel (bool)
* go_to_pose
  * completed (bool)
  * pose
    * rot (float)
    * x (float)
    * y (float)
    * z (float)
  * relative_to_robot (bool)
  * parallel (bool)
* pick_up_object
  * completed (bool)
  * object_id (int)
  * parallel (bool)
* place_object_down 
  * completed (bool)
  * parallel (bool)
* say_text
  * completed (bool)
  * parallel (bool)
  * text (str)
  * duration_scale (float)
  * voice_pitch (float)
* set_backpack_lights
  * completed (bool)
  * parallel (bool)
  * color (int)
* set_head_angle
  * completed (bool)
  * parallel (bool)
  * angle (float)
  * accel (float)
  * max_speed (float)
  * duration (float)
* set_lift_height
  * completed (bool)
  * parallel (bool)
  * height (float)
  * accel (float)
  * max_speed (float)
  * duration (float)
* stop_all_motors
  * completed (bool)
* turn_in_place
  * completed (bool)
  * parallel (bool)
  * angle (float)
  * speed (float)
  * accel (float)
  * angle_tolerance (float)
* turn_towards_face
  * completed (bool)
  * parallel (bool)
  * face_id (int)
  
