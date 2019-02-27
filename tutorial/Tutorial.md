# Introduction

The aim of this tutorial is to teach people somewhat familiar with the Soar cognitive architecture how to write a Soar agent to control a Cozmo robot. It assumes that Soar is already installed on your computer and that you have the Soar-Cozmo Interface code ready to be run. Files associated with each part of the tutorial are included in this directory, and should be able to be sourced presently. When reading a lesson, I strongly suggest opening the associated `.soar` file and keeping it handy so that you can reference it while reading the tutorial. Ideally, by the end of the tutorial, you should understand what the inputs made available to Soar by Cozmo are and what they do, as well aome of the commands Soar can output to Cozmo and what these do. Although the tutorial will not cover every available Cozmo action currently supported, I hope it will cover enough to give you the context and background needed to understand the rest through inspection of the documentation and the interface code. Before getting into examples, we will first go over the higher-level mechanics of how the interface works.

# How It Works

First, it is important to note that the interface code is purely *reactive* to the Soar kernel, which is considered primary. That means the Soar kernel and its cycle is what drives the interface, rather than any internal loop in the interface itself. All of the functionality of the interface is within various *callback* functions, which are triggered by the Soar kernel, execute their code, and then return control to the kernel. Two callback functions in particular are used to provide the two primary functions of the interface: providing information about the Cozmo and its perceptions on the input link and watching the output link for actions the agent wants Cozmo to perform.

## Input

The input is achieved by a callback triggered when the Soar cycle is about to enter the input phase. When the cycle reaches that point, the interface polls the Cozmo robot for all the information which needs to be presented to Soar such as its pose, the status of its lift, and any objects or faces it can see. We will cover the details of how this information is presented later. Once it has the appropriate information from Cozmo, the interface updates the agent's working memory elements through the Soar Markup Language, and passes control back to the kernel, which proceeds into the input phase. By updating the working memory elements before the input phase, we ensure that the agent has the latest information available.

## Output

Control of the Cozmo robot is achieved by a callback which listens for changes to the output link, then scans it for new working memory elements with names of actions Cozmo can take. For example, if the output link is initially empty and Soar adds a new `move-lift` identifier `M1` which has its own attribute `height` set to 0, the new output link would look like 

```
(I3 ^move-lift M1)
  (M2 ^height 0.5)
```

and the output callback would be triggered. It would find the new output link attribute `^move-lift` and its associated identifier, and then see if the string "move-lift" is an action it recognizes. Since it is, it will look at the identifier `M1` and try and find the "height" attribute. The value of the "height" attribute is used in a function call to the Cozmo SDK which will move the lift to the specified level, in this case 50% of its maximum height. Once the Cozmo finishes the action, a "status" attribute is added to the action's identifier and set to "complete", so the final output link looks like

```
(I3 ^move-lift M1)
  (M1 ^height 0.5 ^status complete)
```

Control is then handed back to the Soar kernel, which continues to run its cycle. If more than one new valid action is added to the output link Cozmo will execute all of them before handing back control. The order of execution should be treated as random.

# Lessons

To ground that rather abstract description of the interface, and to provide examples of the specific inputs and outputs the interface provides and handles, we will go through a series of lessons which incrementally build on each other, ultimately producing a Soar agent which will look for a face, then a light cube, then try and bring the light cube to the face.

## Lesson 1: Reset Cozmo's Head and Lift

First, we'll explore how to move Cozmo's head and lift to specific positions using the `move-head` and `move-lift` commands. The `move-head` action sets the angle on Cozmo's head relative to a horizontal plane through its axis of rotation. Thus, if the angle specified is -0.25, Cozmo's head will move so that it forms a -0.25 radian angle with the plane, which ends up having Cozmo look towards the ground. An angle of 0.25 will similarly have Cozmo look upwards. The `move-lift` action moves the lift to a position specified in the command by a real number between 0 and 1. The number indicates the percentage of the lifts maximum height it should move to, so a value of 0 is the lowest possible height for the lift, a value of 1 is the highest, and 0.5 is the lift's midpoint.

We will be using the `move-head` and `move-lift` actions to reset Cozmo's head and lift positions to default ones. Specifically, we want Cozmo to move its head to be parallel with the ground and to lower its lift as far as it can. Together, these actions will help Cozmo see better, since Cozmo often starts with its tilted down, and the lift can occasionally block Cozmo's camera. In order to make sure Cozmo always resets when the Soar agent starts, we will make a slight addition to the usual initialization production for a Soar agent. The initialization proposal rule is a cookie-cutter proposal which just proposes the `initialize-cozmo` operator. The application rule checks for the presence of this operator, and then has two parts. The first is fairly standard: it adds a `^name` attribute to the top-state and sets its value to `cozmo`. The second is what resets the positions of Cozmo's lift and head:

```
(<out>  ^move-head.angle 0.0
        ^move-lift.height 0.0)
```

This part of the right hand side (RHS) adds two working memory elements to the output link, `^move-head` and `move-lift`, and gives them each an attribute, `^angle` for `^move-head` and `^height` for `move-lift`, which are set to 0.0. Recall that the interface listens for new additions to the output link. This means that when this rule fires, the interface will pause the kernel to look for valid actions, which both new WMEs are. The interface will be looking for an "angle" attribute on the "move-head" WME and a "height" attribute on the "move-lift" WME. Since both are present and supply valid values, the interface will execute the specified actions in the Cozmo robot.

## Lesson 2: Saving the Origin Pose

The first input we will be looking at will be Cozmo's pose information, which is always placed by the interface on the agent's input link and will look similar to:

```
(I2 ^pose P1)
    (P1 ^rot 2.733525 ^x 31.371500 ^y 1.045640 ^z 0.000000)
```

The pose identifier will have four attributes with floating point values, `rot`, `x`, `y`, and `z`, indicating Cozmo's rotation on the z (vertical) axis in radians and its position on the x-y plane from the origin in millimeters. Although these values are just estimations based on Cozmo's internal sensors, they are never-the-less useful in keeping track of where Cozmo is. Right now, we are going to make sure that Cozmo also keeps track of where it started by saving Cozmo's initial pose when it starts up. This will involve modifying both the proposal and the application rule we touched on in the last lesson.

First, we need to modify the proposal rule so that the `initialize-cozmo` operator has the initial pose information. In the left hand side (LHS), add a new attribute to search for on the top state, `io.input-link.pose` and assign it ot variable `<p>`, like so:
```
(state <s>  ^superstate nil
           -^name
            ^io.input-link.pose <p>)
```
Then expand `<p>` out to get the actual values of the pose in a separate conditional:
```
(<p> ^rot <rot>
     ^x <x-val>
     ^y <y-val>
     ^z <z-val>)
```
This will look at the pose information on the agent's input link and store the values in the variables `<rot>` (for "rotation"), `<x-val>`, `<y-val>`, and `<z-val>`, so that we can attach them to the operator.

On the RHS, add a new attribute `origin` to the operator `<op>` so it looks like:
```
(<op>   ^name initialize-cozmo
        ^origin <ogn>)
```
and then expand `<ogn>`, adding `rot`, `x`, `y`, and `z` attributes:
```
(<ogn>  ^rot <rot>
        ^x <x-val>
        ^y <y-val>
        ^z <z-val>)
```

Now the operator has the pose information we want to store, which means the application rule an pull directly from the operator. Now we need to modify the application rule so that it actually stores the origin pose on the top-state. First, modify its LHS a bit by looking for an `origin` attribute to the operator and storing it in the variable `<ogn>`. Then, just like above, expand out `<ogn>` so that the agent stores the rotation and location information in `<rot>`, `<x-val>`, `<y-val>`, and `<z-val>`. On the RHS, create an `origin` attribute on the state `<s>`, like so:
```
(<s>    ^name cozmo
        ^origin <origin>)
```
Then expand it out like we have before by adding a new effect:
```
(<origin>   ^rot <rot>
            ^x <x-val>
            ^y <y-val>
            ^z <z-val>)
```
Note that `origin` is stored directly on the top state, rather than in the input link, because it is not an input but a memory. Additionally, because we check for an operator in the LHS, the `origin` WME is  *o-supported*, meaning it will persist even after the rule which added it (`apply*initialize-cozmo`) is retracted. Thus, we have a permanent record of where Cozmo started.