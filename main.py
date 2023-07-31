# Coded by Tea S.
# 2022
from random import randint
import math
from uerrno import EIO
from machine import Pin, I2C, PWM, freq, reset
import utime
import neopixel
import os
import json
from sys import exit
import micropython
import gc
# Overlock pico to max cpu freq
freq(180000000)

# Hardcoded config file for if it doesnt exist on the pico
config = {"buttons": {"fireBtn": 2, "holdBtn": 3, "changeColorBtn": 4},
          "lights": {
    'top': {'length': 9, 'pin': 6, 'flicker': False},
    'core': {'length': 1, 'pin': 7, 'flicker': False},
    'lightTube': {'length': 9, 'pin': 8, 'flicker': False},
    'barrel': {'length': 14, 'pin': 9, 'flicker': False}},
    "colors": {
    'orange': [[255, 80, 0], [255, 255, 255]],
    'blue': [[0, 0, 255], [255, 255, 255]],
    'white': [[240, 240, 255], [50, 50, 50]],
    'off': [[0, 0, 0], [0, 0, 0]],
    'dimWhite':[[25,25,25],[0,0,0]]},
    "servos": {"arm1": {"invert": False, "start": 0, "speed": 300, "curpos": 80, "end": 150, "pin": 21},"arm2": {"invert": False, "start": 0, "speed": 300, "curpos": 80, "end": 150, "pin": 20},"arm3": {"invert": False, "start": 0, "speed": 300, "curpos": 80, "end": 150, "pin": 19}},
    "state": "Main"}


# Load config file from system (it holds all the servo settings and current position so the servos dont judder when it turns back on)

# if "config" in os.listdir():
#     try:
#         file = open("config", "r")
#         config = json.loads(file.readline())
#         file.close()
#     except ValueError:
#         # Problem reading config file, recreate it using the above hardcoded config file
#         print("Unable to read config file...Recreating")
#         file = open("config", "wb")
#         file.write(json.dumps(config))
#         file.close()
# else:
#     # Create config file if it doesn't exist
#     file = open("config", "wb")
#     file.write(json.dumps(config))
#     file.close()


def saveSettings(wherefrom=""):
    print("save - "+wherefrom)
    print(config)
    file = open("config", "wb")
    file.write(json.dumps(config))
    file.close()


print(config)
# ===========================START OF CLASSES ==================================

# Class for controlling and setting servo settings, pass in a config file with all the settings of the servo


class Servo:
    def __init__(self, config):
        self.speed = config['speed']
        self.posMin = config['start']
        self.posMax = config['end']
        self.pin = config['pin']
        self.invert = config['invert']
        self.config = config
        self.targetAngle = config['curpos']
        self.angle = config['curpos']
        self.pwm = PWM(Pin(self.pin, Pin.OUT))
        self.pwm.freq(50)

    def setPos(self, angle, immediate=False):
        if not self.isMoving() or immediate:
            if round(angle) != round(self.angle):
                if angle > self.posMax:
                    angle = self.posMax
                elif angle < self.posMin:
                    angle = self.posMin
                if immediate:
                    self.angle = angle
                    self.targetAngle = angle
                    self.moveServo(angle)
                else:
                    self.targetAngle = angle
                # save angle to config file here
    def setMin(self, min):
        self.posMin = min
        self.setPos(min)

    def setMax(self, max):
        self.posMax = max
        self.setPos(max)

    def setSpeed(self, speed):
        if speed != self.speed:
            self.speed = speed

    def getSpeed(self):
        return self.speed

    def setInvert(self, invert):
        self.invert = invert

    def update(self):
        if self.angle < self.targetAngle:
            self.angle += (self.speed / 100)
        elif self.angle > self.targetAngle:
            self.angle -= (self.speed / 100)
        self.moveServo(int(self.angle))

    def moveServo(self, degrees):
        # limit degrees between 0 and 180
        if degrees > 180:
            degrees = 180
        if degrees < 0:
            degrees = 0
        if self.invert:
            degrees = (180 + 0) - degrees
        # set max and min duty
        maxDuty = 9000
        minDuty = 1500
        # new duty is between min and max duty in proportion to its value
        newDuty = minDuty + (maxDuty - minDuty) * (degrees / 180)
        # servo PWM value is set
        self.pwm.duty_u16(int(newDuty))

    def isMoving(self):
        if round(self.angle) == round(self.targetAngle):
            return False
        else:
            return True

    def open(self, immediate=False):
        self.setPos(self.posMax, immediate=immediate)

    def close(self, immediate=False):
        self.setPos(self.posMin, immediate=immediate)
        # Need to improve this, only works if the servo was set using open() or close()

    def toggle(self):
        if round(self.angle) == round(self.posMax):
            self.close()
        if round(self.angle) == round(self.posMin):
            self.open()

    def saveCurPos(self):
        self.config['curpos'] = self.targetAngle
        saveSettings("savecurpos")
# Pixel class based on RGB tuples, capable of animation from one colour to another, adjusting brightness as a whole and enabling a cool flicker effect (possibly more in the future)
def animateRGB(start_color, end_color, frames):
    """
    Animate the transition from one RGB color to another RGB color.

    Args:
        start_color (tuple): The starting RGB color tuple.
        end_color (tuple): The ending RGB color tuple.
        frames (int): The number of frames in the animation.

    Returns:
        list: A list of RGB color tuples representing the interpolated colors at each frame.
    """
    animations = []
    for i in range(frames):
        progress = i / (frames - 1)
        interpolated_color = interpolateRGB(start_color, end_color, progress)
        animations.append([interpolated_color,[255,255,255]])
    return animations

def interpolateRGB(start_color, end_color, progress):
    """
    Interpolate between two RGB colors based on a given progress.

    Args:
        start_color (tuple): The starting RGB color tuple.
        end_color (tuple): The ending RGB color tuple.
        progress (float): The progress of the transition, ranging from 0 to 1.

    Returns:
        tuple: The interpolated RGB color tuple.
    """
    interpolated_color = []
    for start, end in zip(start_color, end_color):
        interpolated_value = int((1 - progress) * start + progress * end)
        interpolated_color.append(interpolated_value)
    return tuple(interpolated_color)

lightAnimations = {
    "intro":animateRGB(config['colors']['off'][0], config['colors']['white'][0], 30)+animateRGB(config['colors']['white'][0], config['colors']['off'][0], 30),
    "orangeToBlue":animateRGB(config['colors']['orange'][0], config['colors']['off'][0], 20)+animateRGB(config['colors']['off'][0], config['colors']['blue'][0], 20),
    "blueToOrange":animateRGB(config['colors']['blue'][0], config['colors']['off'][0], 20)+animateRGB(config['colors']['off'][0], config['colors']['orange'][0], 20),
    "offToBlue":animateRGB(config['colors']['off'][0], config['colors']['blue'][0], 20),
    "offToOrange":animateRGB(config['colors']['off'][0], config['colors']['orange'][0], 20),
    "pulse":animateRGB(config['colors']['dimWhite'][0], config['colors']['white'][0], 100)+animateRGB(config['colors']['white'][0], config['colors']['dimWhite'][0], 100),
}



class Pixel:
    def __init__(self, speed, brightness, color, flicker=True):
        # Normal Flicker
        self.brightness = 0
        self.color = list(color[0])
        self.flashColor = list(color[1])

        self.targetColor = list(color[0])
        self.targetFlashColor = list(color[1])

        self.randomFlicker = randint(int(1 * speed), int(20 * speed))
        self.speed = speed
        self.randomFlickerCount = 0
        self.randomFlickerOn = 0
        self.brightnessNormal = 0
        self.brightnessFlicker = 0
        self.animationSpeed = 1
        self.isFlicker = flicker
        self.animating = False
        self.currentAnimation = []
        self.setBrightness(brightness)
        self.currentAnimationIndex = 0

    def getPixelState(self):
        self.randomFlickerCount += 1
        self.randomFlickerOn -= 1
        if self.randomFlickerCount >= self.randomFlicker:
            self.randomFlicker = randint(
                int(1 * self.speed), int(20 * self.speed))
            self.randomFlickerOn = 1
            self.randomFlickerCount = 0
        if self.randomFlickerOn > 0 and self.isFlicker:
            return tuple([int(x * self.brightness / 100) for x in self.flashColor])
        else:
            return tuple([int(x * self.brightness / 100) for x in self.color])

    def update(self):
        # Handle colour animation
        if len(self.currentAnimation) > 0 and self.currentAnimationIndex < len(self.currentAnimation):
            self.animating = True
            self.setColor(self.currentAnimation[self.currentAnimationIndex])
            self.currentAnimationIndex += 1
        else:
            self.animating = False
            self.currentAnimationIndex = 0
            self.currentAnimation = []
        return self.getPixelState()

    def getRgb(self):
        return self.rgbCurrent

    def isAnimating(self):
        return self.animating
    # Set the color to animate to

    def animateColor(self, animation):
        if not self.isAnimating():
            self.currentAnimation = animation
            self.animating = True
            self.currentAnimationIndex = 0

    def setColor(self, color):
        if len(color) > 1:
            self.color = list(color[0])
        else:
            self.color = list(color)

    def setAnimationSpeed(self, speed):
        self.animationSpeed = speed

    def setBrightness(self, brightness):
        if self.brightness != brightness:
            if brightness > 100:
                brightness = 100
            elif brightness <= 0:
                brightness = 0
            self.brightness = brightness

    def setFlicker(self, flicker):
        self.isFlicker = flicker
# Class for handling neolight lighting (just holds individual pixels and updates them all the logic happens in the pixel class above)




# NEOLIGHT CLASS: ability to set light 
# 
# 
# 
# 
# 
# 


class NeoLight:
    def __init__(self, config):
        self.config = config
        self.brightness = 0
        self.pin = config['pin']
        self.speed = 1
        self.length = config['length']
        self.np = neopixel.NeoPixel(Pin(config['pin']), config['length'])
        self.pixels = []
        self.color = [[225, 0, 0], [255, 255, 255]]
        self.flicker = config['flicker']
        self.animating = False
        for i in range(len(self.np)):
            pixel = Pixel(self.speed, self.brightness,
                          self.color, self.flicker)
            self.pixels.append(pixel)

    def update(self):
        for index, pixel in enumerate(self.pixels):
            if not pixel.isAnimating():
                self.animating = False
            self.np[index] = pixel.update()
        self.np.write()

    # return if animating
    def isAnimating(self):
        return self.animating
    def resetAnimating(self):
        self.animating = True
        for pixel in self.pixels:
            pixel.animating = True
            pixel.currentAnimationIndex = 0
    def clearAnimating(self):
        self.animating = False
        for pixel in self.pixels:
            pixel.animating = False
            pixel.currentAnimationIndex = 0
            pixel.currentAnimation = []

    def animateColor(self, color, speed=0):
        """
        Animates the color of all pixels in the strip to the specified color.
        
        Args:
            color (int): The color to animate the pixels to.
            speed (int, optional): The speed at which to animate the color change. Defaults to 0.
        
        Returns:
            None
        """
        if not self.isAnimating():
            for pixel in self.pixels:
                pixel.animateColor(color)
            for pixel in self.pixels:
                pixel.animating = True
                pixel.currentAnimationIndex = 0
            self.animating = True

    def setColor(self, color):
        for index, pixel in enumerate(self.pixels):
            if index < self.length:
                pixel.setColor(color)
                self.color = color


    def setColorRange(self, color, start, end):
        for index, pixel in enumerate(self.pixels):
            if index >= start and index < end:
                pixel.setColor(color)
                self.color = color

    def setPixelColor(self, color, pixel):
        self.pixels[pixel].setColor(color)
    # function to return currently set color
    def getColor(self):
        return self.color
    
    # function to get current brightness
    def getBrightness(self):
        return self.brightness

    def setBrightness(self, brightness):
        if self.brightness != brightness:
            if brightness > 100:
                brightness = 100
            elif brightness < 0:
                brightness = 0
            for index, pixel in enumerate(self.pixels):
                if index < self.length:
                    pixel.setBrightness(brightness)
            self.brightness = brightness

    def setFlicker(self, flicker):
        self.flicker = flicker
        for index, pixel in enumerate(self.pixels):
            pixel.setFlicker(flicker)

    def setLength(self, length):
        self.length = length
# Class for handling input buttons, you can set if it should fire off once or press and hold to continually output true after a predefined timeout.


class Button:
    def __init__(self, pin, single=False):
        self.single = single
        self.pin = pin
        self.lock = False
        self.button = Pin(pin, Pin.IN, Pin.PULL_DOWN)
        self.timeout = 5
        self.interval = 5
        self.count = 0
        self.held = False

    def getState(self, single=True):
        """
        Get the state of the button.

        Parameters:
            single (bool): If True, only check the state of the button once. If False, check the state of the button multiple times.

        Returns:
            bool: True if the button is pressed and not locked. False otherwise.
        """
        if self.button.value():
            self.held = True
            if not self.lock:
                self.lock = True
                return True
            else:
                if not single:
                    if self.count >= self.timeout:
                        self.lock = False
                        pass
                    self.count = self.count + 1
                return False
        else:
            self.lock = False
            self.count = 0
            self.held = False
            return False

    def getHeld(self):
        return self.held

    def getCount(self):
        return self.count

    def reset(self):
        self.lock = True
# Basic timer class to count down things and call a method when it reaches its goal


class Timer:
    def __init__(self, start, end, interval, functions=[]):
        self.end = end
        self.start = start
        self.current = start
        self.interval = interval
        self.functions = functions

    def update(self, do):
        if do:
            if self.interval > 0:
                if self.current <= self.end:
                    self.current = self.current + self.interval
            else:
                if self.current >= self.start:
                    self.current = self.current + self.interval
        if self.current >= self.end:
            for function in self.functions:
                if callable(function):
                    function()
            return True
        else:
            return False

    def reset(self):
        self.current = self.start

    def getState(self):
        return self.current

    def setStartEnd(self, start, end):
        self.start = start
        self.end = end


# Initialize all the buttons

fireBtn = Button(config['buttons']['fireBtn'], True)
holdBtn = Button(config['buttons']['holdBtn'], True)
changeColorBtn = Button(config['buttons']['changeColorBtn'], True)




def changeState(toChange):
    global state
    state = toChange


lights = {}
servos = {}

for servo in config['servos']:
    servos[servo] = Servo(config['servos'][servo])


for light in config['lights']:
    lights[light] = NeoLight(config['lights'][light])

for light in lights:
    lights[light].setBrightness(50)
    lights[light].setColor(config['colors']['off'])


# Update servos once before continuing (sets them to the same position as in the config file)
for servo in servos:
    servos[servo].update();

def changeState(toChange):
    global state
    state = toChange


class State():
    def __init__(self, saveState=False):
        self.saveState = saveState

    def enter(self, sm):
        pass

    def update(self, sm):
        pass

    def exit(self, sm):
        pass
    def getStateName(self):
        return self.__class__.__name__

# ========= States ===============


class Intro(State):
    def __init__(self) -> None:
        super().__init__()

    def enter(self, sm):
        for light in lights:
            lights[light].animateColor(lightAnimations['intro'])

    def update(self, sm):
        for light in lights:
            if not lights[light].isAnimating():
                sm.changeState(Main())
    def exit(self, sm):
        for light in lights:
            if light != 'core':
                lights[light].setColor(config['colors'][sm.color])
class Main(State):
    def __init__(self):
        super().__init__()

    def enter(self, sm):
        for servo in servos:
            servos[servo].setPos(80,True)
        lights['lightTube'].setFlicker(False)

    def update(self, sm):
        # Main Loop
        if fireBtn.getState(True):
            sm.changeState(Firing())
        if changeColorBtn.getState(True):
            sm.changeState(ChangeColor())
        if holdBtn.getState(True):
            sm.changeState(Holding())



# change colour state class
class ChangeColor(State):
    def __init__(self):
        super().__init__()

    def enter(self, sm):
        self.animationTimer1 = Timer(0, 25, 1)
        self.animationTimer2 = Timer(0, 25, 1)
        if sm.color == 'blue':
            sm.color = 'orange'
            lights['lightTube'].animateColor(lightAnimations['blueToOrange'])
            lights['top'].animateColor(lightAnimations['blueToOrange'])
            lights['barrel'].animateColor(lightAnimations['blueToOrange'])
        else:
            sm.color = 'blue'
            lights['lightTube'].animateColor(lightAnimations['orangeToBlue'])
            lights['top'].animateColor(lightAnimations['orangeToBlue'])
            lights['barrel'].animateColor(lightAnimations['orangeToBlue'])

    def exit(self, sm):
        pass

    def update(self, sm):
        if not lights['lightTube'].isAnimating():
            sm.changeState(Main())
class Firing(State):
    def __init__(self) -> None:
        super().__init__()

    def enter(self, sm):
        self.fireLength = Timer(0, 22, 1)
        self.beamDelay = Timer(0, 2, 1)
        self.beamCurrentPixel = 0
        lights['top'].setColor(config['colors']['white'])
        for servo in servos:        
            servos[servo].open()

    def exit(self, sm):
        lights['top'].animateColor(lightAnimations['offTo'+sm.color[0].upper() + sm.color[1:]])
        lights['lightTube'].animateColor(lightAnimations['offTo'+sm.color[0].upper() + sm.color[1:]])
        lights['barrel'].animateColor(lightAnimations['offTo'+sm.color[0].upper() + sm.color[1:]])
        for servo in servos:
            servos[servo].setPos(80,True)

    def update(self, sm):
        if self.beamDelay.update(True):
            if self.beamCurrentPixel == 1:
                lights['core'].clearAnimating()
                lights['core'].setColor(config['colors']['off'])
                lights['top'].setColor(config['colors']['off'])
            self.beamDelay.reset()
            if self.beamCurrentPixel < len(lights['lightTube'].pixels):
                lights['lightTube'].setPixelColor(config['colors']['white'],self.beamCurrentPixel)
                if self.beamCurrentPixel-1 >=0:
                    lights['lightTube'].setPixelColor(config['colors']['off'],self.beamCurrentPixel-1)
                self.beamCurrentPixel +=1
            elif self.beamCurrentPixel >= len(lights['lightTube'].pixels):
                lights['lightTube'].setColor(config['colors']['off'])
                lights['barrel'].setColor(config['colors']['white'])

        if self.fireLength.update(True):
            sm.changeState(Main())


class Holding(State):
    def __init__(self) -> None:
        super().__init__()
    def enter(self, sm):
        for servo in servos:
            servos[servo].open()
        lights['lightTube'].setFlicker(True)
    def exit(self, sm):
        pass
    def update(self, sm):
        holdBtn.getState(True)
        if not holdBtn.getHeld():
            sm.changeState(Main())

class StateMachine():
    def __init__(self, starting):
        self.currentState = None
        # Settings
        self.frame = 0
        self.cb = Timer(0, 1, 1)
        self.changeState(starting)
        self.color = 'blue'
        self.pulseTimer = Timer(0, 100, 1)

    def changeState(self, state):
        if self.currentState:
            self.currentState.exit(self)
            # Save new state on exiting old state
            if self.currentState.saveState:
                config['state'] = type(state).__name__
                saveSettings()

        self.currentState = state

        if self.currentState:
            self.currentState.enter(self)
            if self.currentState.saveState:
                config['state'] = type(state).__name__
                saveSettings()

    def getCurrentState(self):
        return self.currentState

    def update(self):
        self.currentState.update(self)
        for servo in servos:
            if servos[servo].isMoving():
                servos[servo].update()
        for light in lights:
            lights[light].update()
        if self.currentState.getStateName() != 'Firing':
            if not lights['core'].isAnimating():
                lights['core'].animateColor(lightAnimations['pulse'])


# Load into previously saved state:
# Only if one of the "safe" states

state = 'Intro'
constructor = globals()[state]

mainLogic = StateMachine(constructor())

# MAIN LOOP
loopstart = utime.time()



while True:
    loopstart = utime.ticks_cpu()
    mainLogic.update()
    delta = utime.ticks_cpu() - loopstart
