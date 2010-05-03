# Fragment shaders, filters, Frame Buffer Object (FBO)
# Authors: Frederik De Bleser, Tom De Smedt
# License: GPL (see LICENSE.txt for details).
# Copyright (c) 2008 City In A Bottle (cityinabottle.org)

from pyglet.gl import *
from math import radians

#=====================================================================================================

pow2 = [2**n for n in range(20)] # [1, 2, 4, 8, 16, 32, 64, ...]

def ceil2(x):
    """ Returns the nearest power of 2 that is higher than x, e.g. 700 => 1024.
    """
    for y in pow2:
        if y >= x: return y
            
def extent2(texture):
    """ Returns the extent of the image data (0.0-1.0, 0.0-1.0) inside its texture owner.
        Textures have a size power of 2 (512, 1024, ...), but the actual image can be smaller.
        For example: a 400x250 image will be loaded in a 512x256 texture.
        Its extent is (0.78, 0.98), the remainder of the texture is transparent.
    """
    return (texture.tex_coords[3], texture.tex_coords[7])
    
def ratio2(texture1, texture2):
    """ Returns the size ratio (0.0-1.0, 0.0-1.0) of two texture owners.
    """
    return (
        float(ceil2(texture1.width)) / ceil2(texture2.width), 
        float(ceil2(texture1.height)) / ceil2(texture2.height)
    )
    
def find(f, seq):
    """ Return first item in the sequence where f(item) == True.
    """
    for item in seq:
        if f(item): return item
        
def clamp(value, a, b):
    """ Returns value clamped between a (minimum) and b (maximum).
    """
    return max(a, min(value, b))

#=====================================================================================================

#--- FRAGMENT SHADER ---------------------------------------------------------------------------------
# A fragment shader is a pixel effect (motion blur, fog, glow) executed on the GPU.
# http://www.lighthouse3d.com/opengl/glsl/index.php?fragmentp
# Fragment shaders are written in GLSL and expect their variables to be set from glUniform() calls.
# The FragmentShader class compiles the source code and has an easy way to pass variables to GLSL.
# e.g. shader = FragmentShader(open("colorize.frag").read())
#      shader.set("color", vec4(1, 0.8, 1, 1))
#      shader.push()
#      image("box.png", 0, 0)
#      shader.pop()

class vector(list): pass

def vec2(f1, f2)         : return vector((f1, f2))
def vec3(f1, f2, f3)     : return vector((f1, f2, f3))
def vec4(f1, f2, f3, f4) : return vector((f1, f2, f3, f4))

COMPILE = "compilation"  # Error occured during glCompileShader().
INSTALL = "installation" # Error occured during glLinkProgram().
class FragmentShaderError(Exception):
    def __init__(self, msg, type=COMPILE):
        self.msg = msg
        self.type = type
    def __str__(self):
        return "error during %s: %s" % (self.type, self.msg)
       
class FragmentShader(object):
   
    def __init__(self, source):
        """ A per-pixel shader effect (blur, fog, glow, ...) executed on the GPU.
            FragmentShader wraps GLSL programs and facilitates passing parameters to them.
            The source parameter is the GLSL source code to execute.
            Raises a FragmentShaderError if the source fails to compile.
            Once compiled, you can set uniform variables in the GLSL source with FragmentShader.set().
        """
        self._source   = source # GLSL source code.
        self._shader   = None
        self._program  = None
        self._active   = False
        self.variables = {}
        self._compile()
    
    def _compile(self):
        # Compile the GLSL source code, checking for errors along the way.
        shader = glCreateShader(GL_FRAGMENT_SHADER)
        length = c_int(-1)
        status = c_int(-1)
        glShaderSource(shader, 1, cast(byref(c_char_p(self._source)), POINTER(POINTER(c_char))), byref(length))
        glCompileShader(shader)
        glGetShaderiv(shader, GL_COMPILE_STATUS, byref(status))
        if status.value == 0:
            e = self._error(shader, COMPILE); glDeleteShader(shader); raise e
        self._shader = shader
        # Create the OpenGL render program from the compiled shader.
        # Each FragmentShader has its own program and you need to switch between them.
        program = glCreateProgram()
        status  = c_int(-1)
        glAttachShader(program, shader)
        glLinkProgram(program)
        glGetProgramiv(program, GL_LINK_STATUS, byref(status))
        if status .value == 0:
            e = self._error(program, LINK); glDeleteProgram(program); raise e
        self._program = program

    def _error(self, obj, type=COMPILE):
        # Get the info for the failed glCompileShader() or glLinkProgram(),
        # return a FragmentShaderError with the error message.
        f1 = type==COMPILE and glGetShaderiv or glGetProgramiv
        f2 = type==COMPILE and glGetShaderInfoLog or glGetProgramInfoLog
        length = c_int(); f1(obj, GL_INFO_LOG_LENGTH, byref(length))  
        msg = ""     
        if length.value > 0:
            msg = create_string_buffer(length.value); f2(obj, length, byref(length), msg)
            msg = msg.value
        return FragmentShaderError(msg, type)

    def get(self, name):
        """ Returns the value of the variable with the given name.
        """
        return self.variables[name]

    def set(self, name, value):
        """ Set the value of the variable with the given name in the GLSL source script.
            Supported variable types are: vec2(), vec3(), vec4(), single int/float, list of int/float.
            Variables will be initialised when FragmentShader.push() is called (i.e. glUseProgram).
        """
        self.variables[name] = value
        if self._active:
            self._set(name, value)
    
    def _set(self, name, value):
        address = glGetUniformLocation(self._program, name)
        # A vector with 2, 3 or 4 floats representing vec2, vec3 or vec4.
        if isinstance(value, vector):
            if len(value) == 2:
                glUniform2f(address, value[0], value[1])
            elif len(value) == 3:
                glUniform3f(address, value[0], value[1], value[2])
            elif len(value) == 4:
                glUniform4f(address, value[0], value[1], value[2], value[3])
        # A list representing an array of ints or floats.
        elif isinstance(value, (list, tuple)):
            if find(lambda v: isinstance(v, float), value):
                array = c_float * len(value)
                glUniform1fv(address, len(value), array(*value))
            else:
                array = c_int * len(value)
                glUniform1iv(address, len(value), array(*value))
        # Single float value.
        elif isinstance(value, float):
            glUniform1f(address, value)
        # Single int value or named texture.
        elif isinstance(value, int):
            glUniform1i(address, value)
        else:
            FragmentShaderError, "don't know how to handle %s" % value.__class__
    
    def push(self):
        """ Installs the program and sets its variables.
            When you use the image() command between shader.push() and shader.pop(),
            the shader's effect will be applied to the image before drawing it.
            To use shader effects in combination with paths,
            draw the path in an offscreen buffer, render it, and apply to effect to the render.
        """
        self._active = True
        glUseProgram(self._program)
        for k, v in self.variables.items():
            self._set(k, v)
            
    def pop(self):
        # Note that shaders can't be nested since they all have their own program,
        # and pop() just removes any active program.
        if self._active == True:
            glUseProgram(0)
            self._active = False

    def _get_source(self):
        return self._source
    def _set_source(self, glsl):
        self._source = glsl
        self._compile()
    source = property(_get_source, _set_source)

    @property
    def active(self):
        return self._active
    
    #def __del__(self):
    #    glDetachShader(self._program, self._shader)
    #    glDeleteShader(self._shader)
    #    glDeleteProgram(self._program)

#=====================================================================================================

#--- FILTER ------------------------------------------------------------------------------------------
# Stores a shader's variables and applies them once push() is called.
# The shader is created only once for perfomance while filters can exist multiple times.
# Textures that are drawn between Filter.push() and Filter.pop() have the effect applied to them.

class Filter(object):
    
    def __init__(self):
        """ Filter combines a FragmentShader with variable settings.
            Variables need to be prepared in Filter.push() before passing them to the shader:
            e.g. creating a list of kernel values, calculating a scale based on image height, ...
            Performance note: create the FragmentShader separately, not during initialization.
        """
        # Shader and its variables need to be stored here.
        self._shader = None
        self.texture = None
        
    def push(self):
        """ Installs the filter so it will be applied to the next image() call.
        """
        # Shader needs to set its variables here:
        # self._shader.set(variable, value)
        self._shader.push()
        
    def pop(self):
        """ Removes the filter.
        """
        self._shader.pop()

#=====================================================================================================

#--- GRADIENT ----------------------------------------------------------------------------------------

LINEAR = "linear"
RADIAL = "radial"

_gradient = {}
_gradient[LINEAR] = FragmentShader('''
uniform sampler2D src;
uniform vec4 clr1;
uniform vec4 clr2;
void main() {
    vec2 v = gl_TexCoord[0].xy;
    gl_FragColor = clr1 * v.y + clr2 * (1.0 - v.y);
}''')
_gradient[RADIAL] = FragmentShader('''
uniform sampler2D src;
uniform vec4 clr1;
uniform vec4 clr2;
void main() {
    vec2 v = gl_TexCoord[0].xy - 0.5;
    float d = 4.0 * (v.x * v.x + v.y * v.y);
    gl_FragColor = clr1 * (1.0 - d) + clr2 * d;
}''')

class LinearGradient(Filter):
    
    def __init__(self, texture, clr1=vec4(0,0,0,1), clr2=vec4(1,1,1,1)):
        self._shader = _gradient[LINEAR]
        self.texture = texture
        self.clr1 = clr1
        self.clr2 = clr2
        
    def push(self):
        self._shader.set("clr1", self.clr1)
        self._shader.set("clr2", self.clr2)
        self._shader.push()

class RadialGradient(Filter):
    
    def __init__(self, texture, clr1=vec4(0,0,0,1), clr2=vec4(1,1,1,1)):
        self._shader = _gradient[RADIAL]
        self.texture = texture
        self.clr1 = clr1
        self.clr2 = clr2
        
    def push(self):
        self._shader.set("clr1", self.clr1)
        self._shader.set("clr2", self.clr2)
        self._shader.push()

#--- COLORIZE ---------------------------------------------------------------------------------------

_colorize = FragmentShader('''
uniform sampler2D src;
uniform vec4 color;
uniform vec4 bias;
void main() {
    vec4 p = texture2D(src, gl_TexCoord[0].xy);
    gl_FragColor = clamp(p * color + bias, 0.0, 1.0);
}''')

class Colorize(Filter):
    
    def __init__(self, texture, color=vec4(1,1,1,1), bias=vec4(0,0,0,0)):
        self._shader = _colorize
        self.texture = texture
        self.color = color
        self.bias  = bias
        
    def push(self):
        self._shader.set("color", self.color)
        self._shader.set("bias",  self.bias)
        self._shader.push()

#--- COLORSPACE -------------------------------------------------------------------------------------
# Helper functions for conversion between RGB and HSB that we can use in other filters.
# Based on "Photoshop math with GLSL shaders" (2009), Romain Dura,
# http://blog.mouaif.org/?p=94

_hsb2rgb = '''
float _hue2rgb(float a, float b, float hue) {
    hue = mod(hue, 1.0);
	if (6.0 * hue < 1.0) return a + (b - a) * 6.0 * hue;
	if (2.0 * hue < 1.0) return b;
	if (3.0 * hue < 2.0) return a + (b - a) * 6.0 * (2.0/3.0 - hue);
	return a;
}
vec3 hsb2rgb(vec3 hsb) {
	if (hsb.y == 0.0) return vec3(hsb.z);
	float b = (hsb.z < 0.5)? hsb.z * (1.0 + hsb.y) : (hsb.y + hsb.z) - (hsb.y * hsb.z);
	float a = 2.0 * hsb.z - b;
	return vec3(
	    _hue2rgb(a, b, hsb.x + (1.0/3.0)),
	    _hue2rgb(a, b, hsb.x),
	    _hue2rgb(a, b, hsb.x - (1.0/3.0))
	);
}'''

_rgb2hsb = '''
vec3 rgb2hsb(vec3 rgb) {
	vec3 hsb = vec3(0.0);
	float a = min(min(rgb.r, rgb.g), rgb.b);
	float b = max(max(rgb.r, rgb.g), rgb.b);
	float c = b - a;
	if (c != 0.0) {
		vec3 d = ((vec3(b) - rgb) / 6.0 + c / 2.0) / c;
		     if (rgb.r == b) hsb.x = d.b - d.g;
		else if (rgb.g == b) hsb.x = d.r - d.b + 1.0/3.0;
		else if (rgb.b == b) hsb.x = d.g - d.r + 2.0/3.0;
		hsb.x = mod(hsb.x, 1.0);
		hsb.y = (hsb.z < 0.5)? c / (a+b) : c / (2.0 - c);
	}
	hsb.z = (a+b) / 2.0;
	return hsb;
}''';

#--- ADJUSTMENTS ------------------------------------------------------------------------------------

BRIGHTNESS = "brightness"
CONTRAST   = "contrast"
SATURATION = "saturation"
HUE        = "hue"

_adjustment = {}
_adjustment[BRIGHTNESS] = FragmentShader('''
uniform sampler2D src;
uniform float m;
void main() {
    vec4 p = texture2D(src, gl_TexCoord[0].xy);
    gl_FragColor = vec4(clamp(p.rgb + m, 0.0, 1.0), p.a);
}''')
_adjustment[CONTRAST] = FragmentShader('''
uniform sampler2D src;
uniform float m;
void main() {
    vec4 p = texture2D(src, gl_TexCoord[0].xy);
    gl_FragColor = vec4(clamp((p.rgb - 0.5) * m + 0.5, 0.0, 1.0), p.a);
}''')
_adjustment[SATURATION] = FragmentShader('''
uniform sampler2D src;
uniform float m;
void main() {
    vec4 p = texture2D(src, gl_TexCoord[0].xy);
    float i = 0.3 * p.r + 0.59 * p.g + 0.11 * p.b;
    gl_FragColor = vec4(
        i * (1.0 - m) + p.r * m,
        i * (1.0 - m) + p.g * m,
        i * (1.0 - m) + p.b * m,
        p.a
    );
}''')
_adjustment[HUE] = FragmentShader(_hsb2rgb + _rgb2hsb + '''
uniform sampler2D src;
uniform float m;
void main() {
    vec4 p = texture2D(src, gl_TexCoord[0].xy);
    vec3 hsb = rgb2hsb(p.rgb);
    hsb.x = hsb.x + m;
    gl_FragColor = vec4(hsb2rgb(hsb).xyz, p.a);
}''') 

class BrightnessAdjustment(Filter):
    
    def __init__(self, texture, m=1.0):
        self._shader = _adjustment[BRIGHTNESS]
        self.texture = texture
        self.m = m
        
    def push(self):
        self._shader.set("m", float(self.m-1))
        self._shader.push()

class ContrastAdjustment(Filter):
    
    def __init__(self, texture, m=1.0):
        self._shader = _adjustment[CONTRAST]
        self.texture = texture
        self.m = m
        
    def push(self):
        self._shader.set("m", float(self.m))
        self._shader.push()

class SaturationAdjustment(Filter):
    
    def __init__(self, texture, m=1.0):
        self._shader = _adjustment[SATURATION]
        self.texture = texture
        self.m = m
        
    def push(self):
        self._shader.set("m", float(max(self.m, 0)))
        self._shader.push()

class HueAdjustment(Filter):
    
    def __init__(self, texture, m=0.0):
        self._shader = _adjustment[HUE]
        self.texture = texture
        self.m = m
        
    def push(self):
        self._shader.set("m", float(self.m));
        self._shader.push()

#--- BRIGHTPASS --------------------------------------------------------------------------------------
# Note: the magic numbers 0.2125, 0.7154, 0.0721 represent that, in RGB, 
# green contributes the most to luminosity while blue hardly contributes anything.
# Thus, luminance L = R*0.2125 + G*0.7154 + B+0.0721

_brightpass = FragmentShader('''
uniform sampler2D src;
uniform float threshold;
void main() {
    vec4 p = texture2D(src, gl_TexCoord[0].xy);
    float L = dot(p.rgb, vec3(0.2125, 0.7154, 0.0721)); // luminance
    gl_FragColor = (L > threshold)? vec4(p.rgb, p.a) : vec4(0.0, 0.0, 0.0, p.a);
}''')

class BrightPass(Filter):
    
    def __init__(self, texture, threshold=0.5):
        self._shader = _brightpass
        self.texture = texture
        self.threshold = threshold
        
    def push(self):
        self._shader.set("threshold", float(self.threshold));
        self._shader.push()

#--- BLUR --------------------------------------------------------------------------------------------
# Based on "Gaussian Blur Filter Shader" (2008), 
# http://www.gamerendering.com/2008/10/11/gaussian-blur-filter-shader/
# Blurring occurs in two steps (requiring an FBO): horizontal blur and vertical blur.
# Separating these two steps reduces the problem to linear complexity (i.e. it is faster).

_blur = '''
uniform sampler2D src;
uniform int kernel;
uniform float radius;
void main() {
    vec2 v = gl_TexCoord[0].xy;
    vec4 p = vec4(0.0);
    float n = float(kernel * kernel);
    for (int i=1; i<kernel; i++) {
        float a = float(i) * radius;
        float b = float(kernel - i) / n;
        p += texture2D(src, vec2(v.x%s, v.y%s)) * b;
        p += texture2D(src, vec2(v.x%s, v.y%s)) * b;
    }    
    p += texture2D(src, vec2(v.x, v.y)) * float(kernel) / n;
    gl_FragColor = p;
}'''
_blur = {
    "horizontal": FragmentShader(_blur % ("-a","","+a","")), # vary v.x
    "vertical"  : FragmentShader(_blur % ("","-a","","+a"))  # vary v.y
}

class HorizontalBlur(Filter):
    
    def __init__(self, texture, kernel=9, scale=1.0):
        self._shader = _blur["horizontal"]
        self.texture = texture
        self.kernel = kernel
        self.scale = scale
        
    def push(self):
        self._shader.set("kernel", int(self.kernel));
        self._shader.set("radius", float(self.scale) / self.texture.width)
        self._shader.push()

class VerticalBlur(Filter):
    
    def __init__(self, texture, kernel=9, scale=1.0):
        self._shader = _blur["vertical"]
        self.texture = texture
        self.kernel = kernel
        self.scale = scale
        
    def push(self):
        self._shader.set("kernel", int(self.kernel));
        self._shader.set("radius", float(self.scale) / self.texture.height)
        self._shader.push()

# It is useful to have a blur in a single pass as well,
# which we can use as a parameter for the image() command.
# However, for a simple 3x3 in separate steps => 6 calculations, single pass => 9 calculations.
_blur["gaussian3x3"] = FragmentShader('''
uniform sampler2D src;
uniform vec2 radius;
void main(void) {
    float dx = radius.x;
    float dy = radius.y;
    vec2 v = gl_TexCoord[0].xy;
    vec4 p = vec4(0.0);
    p  = 4.0 * texture2D(src, v);
    p += 2.0 * texture2D(src, v + vec2(+dx, 0.0));
    p += 2.0 * texture2D(src, v + vec2(-dx, 0.0));
    p += 2.0 * texture2D(src, v + vec2(0.0, +dy));
    p += 2.0 * texture2D(src, v + vec2(0.0, -dy));
    p += 1.0 * texture2D(src, v + vec2(+dx, +dy));
    p += 1.0 * texture2D(src, v + vec2(-dx, +dy));
    p += 1.0 * texture2D(src, v + vec2(-dx, -dy));
    p += 1.0 * texture2D(src, v + vec2(+dx, -dy));
    gl_FragColor = p / 16.0;
}''')

class Gaussian3x3Blur(Filter):
    
    def __init__(self, texture, scale=1.0):
        self._shader = _blur["gaussian3x3"]
        self.texture = texture
        self.scale = scale
        
    def push(self):
        x = float(self.scale) / self.texture.width
        y = float(self.scale) / self.texture.height
        self._shader.set("radius", vec2(x, y))
        self._shader.push()

#--- COMPOSITING -------------------------------------------------------------------------------------

# Compositing function.
# It will be reused in alpha compositing and blending filters below.
# It prepares pixels p1 and p2, which need to be mixed into vec4 p.
_compositing = '''
uniform sampler2D src1;
uniform sampler2D src2;
uniform vec2 ratio;
uniform float alpha;
void main() {
    vec2 v  = gl_TexCoord[0].xy;
    vec4 p1 = texture2D(src1, v.xy);
    vec4 p2 = texture2D(src2, v.xy * ratio);
    %s
    p = (v.x * ratio.x > 1.0 || v.y * ratio.y > 1.0)? p1 : p;
    gl_FragColor = p;
}'''

class Compositing(Filter):
    
    def __init__(self, shader, texture, blend, alpha=1.0):
        """ A filter that mixes a base image (the destination) with a blend image (the source).
            Used to implement alpha compositing and blend modes.
        """
        self._shader = shader
        self.texture = texture
        self.blend = blend
        self.alpha = alpha    

    def push(self):
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(self.texture.target, self.texture.id)        
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(self.blend.target, self.blend.id)
        glActiveTexture(GL_TEXTURE0)
        self._shader.set("src1", 0)
        self._shader.set("src2", 1)
        self._shader.set("ratio", vec2(*ratio2(self.texture, self.blend))) # Size proportion.
        self._shader.set("alpha", self.alpha)
        self._shader.push()

#--- ALPHA TRANSPARENCY ------------------------------------------------------------------------------

_alpha = {}
_alpha["transparency"] = FragmentShader('''
uniform sampler2D src;
uniform float alpha;
void main() {
    vec4 p = texture2D(src, gl_TexCoord[0].xy);
    gl_FragColor = vec4(p.rgb, p.a * alpha);
}''')
_alpha["mask"] = FragmentShader(_compositing % '''
    vec4 p = vec4(p1.rgb, p1.a * (1.0 - p2.r * alpha));
'''.strip())

class AlphaTransparency(Filter):

    def __init__(self, texture, alpha=1.0):
        self._shader = _alpha["transparency"]
        self.texture = texture
        self.alpha = alpha
        
    def push(self):
        self._shader.set("alpha", float(max(0, min(1, self.alpha))))
        self._shader.push()

class AlphaMask(Compositing):

    def __init__(self, texture, blend, alpha=1.0):
        Compositing.__init__(self, _alpha["mask"], texture, blend, alpha)
        self._shader = _alpha["mask"]

#--- BLEND MODES -------------------------------------------------------------------------------------
# Based on "Photoshop math with GLSL shaders" (2009), Romain Dura,
# http://blog.mouaif.org/?p=94

ADD      = "add"      # Pixels are added.
SUBTRACT = "subtract" # Pixels are subtracted.
LIGHTEN  = "lighten"  # Lightest value for each pixel.
DARKEN   = "darken"   # Darkest value for each pixel.
MULTIPLY = "multiply" # Pixels are multiplied, resulting in a darker image.
SCREEN   = "screen"   # Pixels are inverted/multiplied/inverted, resulting in a brighter picture.
OVERLAY  = "overlay"  # Combines multiply and screen: light parts become ligher, dark parts darker.
HUE      = "hue"      # Hue from the blend image, brightness and saturation from the base image.

_blendf = _compositing % '''
    vec3 w  = vec3(1.0); // white
    %s
    p = mix(p1, clamp(p, 0.0, 1.0), p2.a * alpha);
'''.strip()
_blend = {}
_blend[ADD]      = 'vec4 p = vec4(p1.rgb + p2.rgb, 1.0);'
_blend[SUBTRACT] = 'vec4 p = vec4(p1.rgb + p2.rgb - 1.0, 1.0);'
_blend[LIGHTEN]  = 'vec4 p = vec4(max(p1.rgb, p2.rgb), 1.0);'
_blend[DARKEN]   = 'vec4 p = vec4(min(p1.rgb, p2.rgb), 1.0);'
_blend[MULTIPLY] = 'vec4 p = vec4(p1.rgb * p2.rgb, 1.0);'
_blend[SCREEN]   = 'vec4 p = vec4(w - (w - p1.rgb) * (w - p2.rgb), 1.0);'
_blend[OVERLAY]  = '''
    float L = dot(p1.rgb, vec3(0.2125, 0.7154, 0.0721)); // luminance
    vec4 a = vec4(2.0 * p1.rgb * p2.rgb, 1.0);
    vec4 b = vec4(w - 2.0 * (w - p1.rgb) * (w - p2.rgb), 1.0);
    vec4 p = (L < 0.45)? a : (L > 0.55)? b : vec4(mix(a.rgb, b.rgb, (L - 0.45) * 10.0), 1.0);
'''
_blend[HUE] = '''
    vec3 h1 = rgb2hsb(p1.rgb);
    vec3 h2 = rgb2hsb(p2.rgb);
    vec4 p = vec4(hsb2rgb(vec3(h2.x, h1.yz)).rgb, p1.a);
'''

for f in _blend.keys():
    src = _blendf % _blend[f].strip()
    src = f==HUE and _rgb2hsb + _hsb2rgb + src or src # Hue blend requires rgb2hsb() function.
    _blend[f] = FragmentShader(src)

class Blend(Compositing):
    
    def __init__(self, mode, texture, blend, alpha=1.0):
        Compositing.__init__(self, _blend[mode], texture, blend, alpha)

#--- DISTORTION --------------------------------------------------------------------------------------
# Based on "PhotoBooth Demystified" (2007), Libero Spagnolini, 
# http://dem.ocracy.org/libero/photobooth/

PINCH   = "pinch"  # Radius grows faster near the center of the effect.
TWIRL   = "twirl"  # Decreasing offset is added to the angle while moving down the radius.
SPLASH  = "splash" # Light-tunnel effect by capping the radius.
BUMP    = "bump"   # Radius grows slower near the center of the effect.
DENT    = "dent"
FISHEYE = "fisheye"
STRETCH = "stretch"
MIRROR  = "mirror"

# Distortion function.
# - vec2 offset: horizontal and vertical offset from the image center (-0.5-0.5).
# - vec2 extent: the actual size of the image (0.0-1.0) in the texture.
#   Textures have a size power of 2 (512, 1024, ...) but the actual image may be smaller.
#   We need to know the extent of the image in the texture to calculate its center.
# - float ratio: the ratio between width and height, so the effect doesn't get stretched.
# - float m: the magnitude of the effect (e.g. radius, ...) 
# - float i: the intensity of the effect (e.g. number of rotations, ...) 
# - vec2 n: a normalized texture space between -1.0 and 1.0 (instead of 0.0-1.0).
_distf = '''
uniform sampler2D src;
uniform vec2 offset;
uniform vec2 extent;
uniform float ratio;
uniform float m;
uniform float i;
void main() {
    vec2 v = gl_TexCoord[0].xy;
    vec2 d = extent + extent * offset;
    vec2 n = 2.0 * v - 1.0 * d;
    n.x *= ratio;
    %s
    n.x /= ratio;
    v = n / 2.0 + 0.5 * d;
    gl_FragColor = texture2D(src, v); 
}'''
# Polar coordinates.
# Most of the effects are based on simple angle and radius transformations.
# After the transformations, convert back to cartesian coordinates n.
_polar = '''
    float r = length(n);
    float phi = atan(n.y, n.x);
    %s
    n = vec2(r*cos(phi), r*sin(phi));
'''.strip()
_distortion = {}
_distortion[PINCH]   = 'r = pow(r, 1.0/i) * m;'
_distortion[TWIRL]   = 'phi = phi + (1.0 - smoothstep(-m, m, r)) * i;' #ok
_distortion[SPLASH]  = 'if (r > m) r = m;' #ok
_distortion[BUMP]    = 'r = r * smoothstep(1.0/i, m, r);'
_distortion[DENT]    = 'r = 2.0 * r - r * smoothstep(0.0, 0.7, r);'
_distortion[FISHEYE] = 'r = r * r / sqrt(2.0);'
_distortion[MIRROR]  = 'n.x = n.x * sign(n.x);'
_distortion[STRETCH] = '''
    vec2 s = sign(n);
    n = abs(n);
    n = (1.0-i) * n + i * smoothstep(m*0.25, m, n) * n;
    n = s * n;
'''.strip()#ok

for f in (PINCH, TWIRL, SPLASH, BUMP, DENT, FISHEYE):
    _distortion[f] = FragmentShader(_distf % _polar % _distortion[f])
for f in (STRETCH, MIRROR):
    _distortion[f] = FragmentShader(_distf % _distortion[f])

class Distortion(Filter):
    
    def __init__(self, effect, texture, dx=0, dy=0, m=1.0, i=1.0):
        """ Distortion filter with dx, dy offset from the center (between -0.5 and 0.5),
            magnitude m as the radius of effect, intensity i as the depth of the effect.
        """
        self._shader = _distortion[effect]
        self.texture = texture
        self.dx = dx
        self.dy = dy
        self.m = m
        self.i = i
    
    # Center offset can also be set in absolute coordinates (e.g. pixels):
    def _get_abs_dx(self): 
        return int(self.dx * self.texture.width)
    def _get_abs_dy(self): 
        return int(self.dy * self.texture.height)
    def _set_abs_dx(self, v): 
        self.dx = float(v) / self.texture.width
    def _set_abs_dy(self, v): 
        self.dy = float(v) / self.texture.height
    abs_dx = property(_get_abs_dx, _set_abs_dx)
    abs_dy = property(_get_abs_dy, _set_abs_dy)

    def push(self):
        w  = float(self.texture.width)
        h  = float(self.texture.height)
        w2 = float(ceil2(w))
        h2 = float(ceil2(h))
        self._shader.set("extent", vec2(w/w2, h/h2))
        self._shader.set("offset", vec2(float(2*self.dx), float(2*self.dy)))
        self._shader.set("ratio", w2/h2)
        self._shader.set("m", float(self.m))
        self._shader.set("i", float(self.i))
        self._shader.push()

#=====================================================================================================

#--- FRAME BUFFER OBJECT -----------------------------------------------------------------------------
# Based on "Frame Buffer Object 101" (2006), Rob Jones, 
# http://www.gamedev.net/reference/articles/article2331.asp

def _texture(width, height):
    return pyglet.image.Texture.create(width, height)  

class FBOError(Exception):
    pass

class FBO:
    
    def __init__(self, width, height):
        """ "FBO" is an OpenGL extension to do "Render to Texture", drawing in an offscreen buffer.
            It is useful as a place to chain multiple shaders,
            since each shader has its own program and we can only install one program at a time.
        """
        self.id = c_uint(0)
        glGenFramebuffersEXT(1, byref(self.id))
        self._texture = None
        self._active = False
        self._init(width, height)
        
    def _init(self, width, height):
        self._texture = _texture(width, height)  

    @property
    def width(self):
        return self._texture.width
    
    @property
    def height(self):
        return self._texture.height

    @property
    def texture(self):
        return self._texture
    
    @property
    def active(self):
        return self._active
    
    def push(self):
        """ Between push() and pop(), all drawing is done offscreen in FBO.texture.
            The offscreen buffer has its own transformation state,
            so any translate(), rotate() etc. does not affect the onscreen canvas.
        """
        glBindTexture(self._texture.target, self._texture.id)
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, self.id.value)
        glFramebufferTexture2DEXT(
            GL_FRAMEBUFFER_EXT, 
            GL_COLOR_ATTACHMENT0_EXT, 
            self._texture.target, 
            self._texture.id, 
            self._texture.level
        )
        # FBO's can fail when not supported by your graphics hardware,
        # when supplied an image of size 0 or unequal width/height.
        # Check after glBindFramebufferEXT() and glFramebufferTexture2DEXT().
        if glCheckFramebufferStatusEXT(GL_FRAMEBUFFER_EXT) != GL_FRAMEBUFFER_COMPLETE_EXT:
            msg = self._texture.width == self._texture.height == 0 and "width=0, height=0." or ""
            raise FBOError, msg
        # Separate the offscreen from the onscreen transform state.
        glPushMatrix()
        glLoadIdentity()
        # Blending transparent images in a transparent FBO doesn't work right.
        # Because alpha is premultiplied, an image with 50% transparency
        # will come out with 25% transparency.
        # http://www.opengl.org/discussion_boards/ubbthreads.php?ubb=showflat&Number=257630
        # http://www.openframeworks.cc/forum/viewtopic.php?f=9&t=2215
        # This blend mode gives somewhat better results:
        glBlendFuncSeparate(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_ONE, GL_ONE_MINUS_SRC_ALPHA)
        self._active = True
    
    def pop(self):
        """ Reverts to the onscreen canvas. 
            The contents of the offscreen buffer can be retrieved with FBO.texture.
        """
        glPopMatrix()
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, 0)
        # Reset to the normal blending mode.
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self._active = False
    
    def render(self):
        """ Executes the drawing commands in FBO.draw() offscreen and returns image.
            This is useful if you have a class that inherits from FBO with a draw() method.
        """
        self.push()
        self.draw()
        self.pop()
        return self.texture
        
    def draw(self):
        pass
        
    def slice(self, x, y, width, height):
        """ Returns a portion of the offscreen buffer as an image.
        """
        return self._texture.get_region(x, y, width, height) 
    
    def clear(self):
        """ Clears the contents of the offscreen buffer by attaching a new texture to it.
            If you do not explicitly clear the buffer, the content from previous drawing
            between FBO.push() and FBO.pop() is retained.
        """
        if self._active:
            raise FBOError, "can't clear FBO when active."
        self._init(self.width, self.height)

    def resize(self, width, height):
        """ Resizes the offscreen buffer by attaching a new texture to it.
        """
        if self._active:
            raise FBOError, "can't resize FBO when active."
        self._init(width, height) 

    #def _init_depthbuffer(self):
    #    # Some of these steps should happen after the framebuffer has been bound I think.
    #    self._depthbuffer = c_uint(0)
    #    glGenRenderbuffersEXT(1, byref(self._depthbuffer))
    #    glBindRenderbufferEXT(GL_RENDERBUFFER_EXT, self._depthbuffer)
    #    glRenderbufferStorageEXT(GL_RENDERBUFFER_EXT, GL_DEPTH_COMPONENT, width, height)
    #    glFramebufferRenderbufferEXT(
    #        GL_FRAMEBUFFER_EXT,
    #        GL_DEPTH_ATTACHMENT_EXT,
    #        GL_RENDERBUFFER_EXT,
    #        self._depthbuffer
    #    )
    
    #def _delete_depthbuffer(self):
    #    glDeleteRenderbuffersEXT(1, self._depthbuffer)
    
    #def __del__(self):
    #    glDeleteFramebuffersEXT(1, self.id)

OffscreenBuffer = FBO

#=====================================================================================================

#--- OFFSCREEN RENDERING -----------------------------------------------------------------------------
# Uses an offscreen buffer to render filters and drawing commands to images.

_fbo = FBO(640, 480)

def _image(*args, **kwargs):
    # Function that draws a texture.
    # We use the image() command from context.py
    # This should be reorganized (e.g. image.py module that is imported by context.py and shader.py).
    pass
    
from context import image as _image, texture
from context import Image

def render(img, filter=None, clear=True):
    """ Returns a new Image object with the given filter applied to it.
        - img   : an image that can be passed to the image() command.
        - filter: an instance of the Filter class, with parameters set.
        - clear : if True, clears the contents of the offscreen buffer and resizes it to the image.
    """
    # For file paths, textures and Pixel objects, create an Image first.
    if not isinstance(img, Image):
        img = Image(img)
    if clear == True:
        _fbo.resize(img.texture.width, img.texture.height)
    _fbo.push()
    if filter != None:
        filter.texture = img.texture # Register the current texture with the filter.
        filter.push()
    # Note: Image.alpha and Image.color attributes won't work here,
    # because the shader overrides the default drawing behavior.
    img.draw() # XXX x y
    if filter != None:
        filter.pop()
    _fbo.pop()
    return img.copy(texture=_fbo.texture)
    
def procedural(function, width, height, clear=True):
    """ Returns an Image object from a function containing drawing commands (e.g. a procedural image).
        This is useful when, for example, you need to render filters on paths.
    """
    if clear == True:
        _fbo.resize(width, height)
    _fbo.push()
    function()
    _fbo.pop()
    return Image(_fbo.texture)
    
#--- OFFSCREEN FILTERS -------------------------------------------------------------------------------

def gradient(width, height, clr1=(0,0,0,1), clr2=(1,1,1,1), type=LINEAR):
    """ Generates a gradient image and returns it.
        - width : the width of the image.
        - height: the height of the image.
        - clr1  : a Color (or a tuple) that defines the bottom (or inner) color.
        - clr2  : a Color (or a tuple) that defines the top (or outer) color.
        - type  : either LINEAR or RADIAL.
    """
    f = type==LINEAR and LinearGradient or RadialGradient
    img = Image(_texture(ceil2(width), ceil2(height)))
    img = render(img, filter=f(img, vec4(*clr1), vec4(*clr2)))
    # If the given dimensions where not power of 2,
    # scale down the gradient to the given dimensions.
    if width != img.width or height != img.height:
        _fbo.resize(width, height)
        _fbo.push()
        img.width  = width
        img.height = height
        img.draw()
        _fbo.pop()
        return img.copy(texture=_fbo.texture)
    return img

def colorize(img, color=(1,1,1,1), bias=(0,0,0,0)):
    """ Applies a colorize filter to the image and returns the colorized image.
        - color: a Color (or a tuple) of RGBA-values to multiply with each image pixel.
        - bias : a Color (or a tuple) of RGBA-values to add to each image pixel.
    """
    return render(img, filter=Colorize(img, vec4(*color), vec4(*bias)))

def adjust(img, brightness=1.0, contrast=1.0, saturation=1.0, hue=0.0):
    """ Applies color adjustment filters to the image and returns the adjusted image.
        - brightness: the overall lightness or darkness (0.0 is a black image).
        - contrast  : the difference in brightness between regions.
        - saturation: the intensity of the colors (0.0 is a grayscale image).
        - hue       : the shift in hue (1.0 is 360 degrees on the color wheel).
    """
    if brightness != 1: img = render(img, filter=BrightnessAdjustment(img, brightness))
    if contrast   != 1: img = render(img, filter=ContrastAdjustment(img, contrast))
    if saturation != 1: img = render(img, filter=SaturationAdjustment(img, saturation))
    if hue        != 0: img = render(img, filter=HueAdjustment(img, hue))
    return img
    
def desaturate(img):
    """ Returns a grayscale version of the image.
    """
    return render(img, filter=SaturationAdjustment(img, 0.0))

def brightpass(img, threshold=0.3):
    """ Applies a bright pass filter, where pixels whose luminance falls below the threshold are black.
    """
    return render(img, filter=BrightPass(img, threshold))

def blur(img, kernel=9, scale=1.0, amount=1, cumulative=True):
    """ Applies a blur filter to the image and returns the blurred image.
        - kernel: the size of the convolution matrix (e.g. 9 = 9x9 convolution kernel).
        - scale : the radius of the effect, a higher scale will create a rougher but faster blur.
        - amount: the number of the times to apply the blur filter;
                  because blurred layers are pasted on top of each other cumulatively
                  this produces a nicer effect than repeatedly using blur() in a for-loop
                  (which blurs the blurred).
    """
    for i in range(amount):
        clear = i==0 or not cumulative
        img = render(img, filter=HorizontalBlur(img, kernel, scale), clear=clear)
        img = render(img, filter=VerticalBlur(img, kernel, scale), clear=clear)
    return img

def transparent(img, alpha=1.0):
    """ Returns a transparent version of the image.
        - alpha: the percentage of the original opacity of the image (0.0-1.0).
    """
    return render(img, filter=AlphaTransparency(img, alpha))
    
def mask(img1, img2, alpha=1.0):
    """ Applies the second image as an alpha mask to the first image.
        The second image must be a grayscale image, where the black areas
        make the first image transparent (e.g. punch holes in it).
    """
    return render(img1, filter=AlphaMask(img1, img2, alpha))

def add(img1, img2, alpha=1.0):
    return render(img1, filter=Blend(ADD, img1, img2, alpha))

def subtract(img1, img2, alpha=1.0):
    return render(img1, filter=Blend(SUBTRACT, img1, img2, alpha))

def lighten(img1, img2, alpha=1.0):
    return render(img1, filter=Blend(LIGHTEN, img1, img2, alpha))
    
def darken(img1, img2, alpha=1.0):
    return render(img1, filter=Blend(DARKEN, img1, img2, alpha))

def multiply(img1, img2, alpha=1.0):
    return render(img1, filter=Blend(MULTIPLY, img1, img2, alpha))
    
def screen(img1, img2, alpha=1.0):
    return render(img1, filter=Blend(SCREEN, img1, img2, alpha))
    
def overlay(img1, img2, alpha=1.0):
    return render(img1, filter=Blend(OVERLAY, img1, img2, alpha))
    
def hue(img1, img2, alpha=1.0):
    return render(img1, filter=Blend(HUE, img1, img2, alpha))
    
def glow(img, intensity=0.5, amount=1):
    """ Returns the image blended with a blurred version, yielding a glowing effect.
        - intensity: the opacity of the blur (0.0-1.0).
        - amount   : the number of times to blur. 
    """
    b = blur(img, kernel=9, scale=1.0, amount=max(1,amount))
    return add(img, b, alpha=intensity)

def bloom(img, intensity=0.5, amount=1, threshold=0.3):
    """ Returns the image blended with a blurred brightpass version, yielding a "magic glow" effect.
        - intensity: the opacity of the blur (0.0-1.0).
        - amount   : the number of times to blur.
        - threshold: the luminance threshold of pixels that light up.
    """
    b = brightpass(img, threshold)
    b = blur(b, kernel=9, scale=1.0, amount=max(1,amount))
    return add(img, b, alpha=intensity)

# m: zoom in the image when smaller (0.0-1.0)
# i: pinch depth (no pinch when 1.0, bulge when smaller than 1) (0.25-10.0)
def pinch(img, dx=0, dy=0, m=1.0, i=1.8):
    return render(img, filter=Distortion(PINCH, img, dx-0.5, dy-0.5, m, i))

def twirl(img, dx=0.5, dy=0.5, radius=1.0, angle=180.0):
    """ Returns the image with a twirl distortion applied to it.
        - dx: horizontal origin of the effect, between 0.0 and 1.0.
        - dy: vertical origin of the effect, between 0.0 and 1.0.
        - radius: the radius of the effect, proportional to the image size.
        - angle: the amount of rotation in degrees.
    """
    return render(img, filter=Distortion(TWIRL, img, dx-0.5, dy-0.5, m=radius, i=radians(angle)))

def splash(img, dx=0, dy=0, radius=0.5):
    """ Returns the image with a light-tunnel distortion applied to it.
        - dx: horizontal origin of the effect, between 0.0 and 1.0.
        - dy: vertical origin of the effect, between 0.0 and 1.0.
        - radius: the radius of the unaffected area, proportional to the image size.
    """
    return render(img, filter=Distortion(SPLASH, img, dx-0.5, dy-0.5, m=radius, i=0))

def bump(img, dx=0, dy=0, m=1.0, i=1.0):
    return render(img, filter=Distortion(BUMP, img, dx-0.5, dy-0.5, m, i))
    
def dent(img, dx=0, dy=0, m=1.0, i=1.0):
    return render(img, filter=Distortion(DENT, img, dx-0.5, dy-0.5, m, i))

def fisheye(img, dx=0, dy=0, m=1.0, i=1.0):
    return render(img, filter=Distortion(FISHEYE, img, dx-0.5, dy-0.5, m, i))

def stretch(img, dx=0, dy=0, radius=0.5, zoom=1.0):
    """ Returns the image with a zoom box distortion applied to it.
        - dx: horizontal origin of the effect, between 0.0 and 1.0.
        - dy: vertical origin of the effect, between 0.0 and 1.0.
        - radius: the radius of the affected area, proportional to the image size.
        - zoom: the amount to zoom in (0.0-2.0, where 1.0 means 1x zoomed in, or 200%).
    """
    return render(img, filter=Distortion(STRETCH, img, dx-0.5, dy-0.5, m=max(0,radius), i=clamp(zoom*0.5,0,1)))

def mirror(img, dx=0, dy=0, m=1.0, i=1.0):
    return render(img, filter=Distortion(MIRROR, img, dx-0.5, dy-0.5, m, i))
    
#--- ONSCREEN FILTERS --------------------------------------------------------------------------------
# These can be used directly as filter parameter for the image() command.
    
def colorized(color=(1,1,1,1), bias=(0,0,0,0)):
    return Colorize(None, vec4(*color), vec4(*bias))
    
def blurred(scale=1.0):
    return Gaussian3x3Blur(None, scale)

def desaturated():
    return SaturationAdjustment(None, 0.0)
    
def blended(mode, img, alpha=1.0):
    return Blend(mode, None, img, alpha)
    
def distorted(effect, dx=0, dy=0, m=1.0, i=1.0):
    return Distortion(effect, None, dx, dy, m, i)

#-----------------------------------------------------------------------------------------------------
# Some sketches for a future convolution kernel:

_kernel = '''
const int KERNEL = 9;
uniform float kernel[KERNEL];
uniform float offset[KERNEL*2];

uniform sampler2D colorMap;
uniform float width;
uniform float height;

void main() {
    vec4 sum = vec4(0.0);
    for(int i=0; i<KERNEL; i++) {
        vec2 o = gl_TexCoord[0].st + vec2(offset[i*2], offset[i*2+1]);
        //if(o.s > 0.005) {
            vec4 tmp = texture2D(colorMap, o);
            sum += tmp * kernel[i];
        //}
    }
    sum.a = gl_TexCoord[0].a;
    //sum.a = texture2D(colorMap, gl_TexCoord[0].st).a;
    if ( texture2D(colorMap, gl_TexCoord[0].st).a < 0.01 ) { sum.a = 0.0; }
    gl_FragColor = sum;
    //gl_FragColor = texture2D(colorMap, gl_TexCoord[0].st);
}
'''
k = [
    1.0, 2.0, 1.0,
    2.0, 4.0, 2.0,
    1.0, 2.0, 1.0
]
k = [x/sum(k) for x in k]

class ConvolutionKernel(Filter):
    def __init__(self, texture, scale=1.0, kernel=5):
        self._shader = FragmentShader(_kernel)
        self.texture = texture
        self.scale = scale    
    def push(self):
        self._shader.set("width", self.texture.width)
        self._shader.set("height", self.texture.height)
        self._shader.set("kernel", k)
        o = [
            -1,-1,  0,-1,  1,-1, 
            -1, 0,  0, 0,  1, 0, 
            -1, 1,  0, 1,  1, 1
        ]
        for i in range(9):
		    o[i*2  ] *= 1.0/self.texture.width
		    o[i*2+1] *= 1.0/self.texture.height
        self._shader.set("offset", o)
        #self._shader.set("src_tex_offset0", vec2(4.0/self.texture.width, 4.0/self.texture.height))
        #self._shader.set("offset", vec2(self.scale/self.texture.width, self.scale/self.texture.height))
        self._shader.push()

