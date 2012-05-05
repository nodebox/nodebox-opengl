
# Fragment shaders, filters, Frame Buffer Object (FBO)
# Authors: Tom De Smedt, Frederik De Bleser
# License: BSD (see LICENSE.txt for details).
# Copyright (c) 2008 City In A Bottle (cityinabottle.org)
# http://cityinabottle.org/nodebox

from pyglet.gl    import *
from pyglet.image import Texture, SolidColorImagePattern
from context      import Image, texture
from geometry     import lerp, clamp
from math         import radians
from ctypes       import byref, cast, c_char, c_char_p, c_uint, c_int, pointer, POINTER

def next(generator, default=None):
    try: 
        return generator.next()
    except StopIteration:
        return default

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

#=====================================================================================================

#--- SHADER ------------------------------------------------------------------------------------------
# A shader is a pixel effect (motion blur, fog, glow) executed on the GPU.
# The effect has two distinct parts: a vertex shader and a fragment shader.
# The vertex shader retrieves the coordinates of the current pixel.
# The fragment shader manipulates the color of the current pixel.
# http://www.lighthouse3d.com/opengl/glsl/index.php?fragmentp
# Shaders are written in GLSL and expect their variables to be set from glUniform() calls.
# The Shader class compiles the source code and has an easy way to pass variables to GLSL.
# e.g. shader = Shader(fragment=open("colorize.frag").read())
#      shader.set("color", vec4(1, 0.8, 1, 1))
#      shader.push()
#      image("box.png", 0, 0)
#      shader.pop()

DEFAULT = "default"
DEFAULT_VERTEX_SHADER = '''
void main() { 
    gl_TexCoord[0] = gl_MultiTexCoord0; 
    gl_Position = ftransform(); 
}'''
DEFAULT_FRAGMENT_SHADER = '''
uniform sampler2D src;
void main() {
    gl_FragColor = texture2D(src, gl_TexCoord[0].xy);
}'''

class vector(tuple): 
    pass
    
def vec2(f1, f2):
    return vector((f1, f2))
def vec3(f1, f2, f3):
    return vector((f1, f2, f3))
def vec4(f1, f2, f3, f4):
    return vector((f1, f2, f3, f4))

COMPILE = "compile" # Error occurs during glCompileShader().
BUILD   = "build"   # Error occurs during glLinkProgram().
class ShaderError(Exception):
    def __init__(self, value, type=COMPILE):
        Exception.__init__(self, "%s error: %s" % (type, value))
        self.value = value
        self.type  = type

class Shader(object):
   
    def __init__(self, vertex=DEFAULT, fragment=DEFAULT):
        """ A per-pixel shader effect (blur, fog, glow, ...) executed on the GPU.
            Shader wraps a compiled GLSL program and facilitates passing parameters to it.
            The fragment and vertex parameters contain the GLSL source code to execute.
            Raises a ShaderError if the source fails to compile.
            Once compiled, you can set uniform variables in the GLSL source with Shader.set().
        """
        if vertex == DEFAULT:
            vertex = DEFAULT_VERTEX_SHADER
        if fragment == DEFAULT:
            fragment = DEFAULT_FRAGMENT_SHADER
        self._vertex   = vertex   # GLSL source for vertex shader.
        self._fragment = fragment # GLSL source for fragment shader.
        self._compiled = []
        self._program  = None
        self._active   = False
        self.variables = {}
        self._build()
    
    def _compile(self, source, type=GL_VERTEX_SHADER):
        # Compile the GLSL source code, either as GL_FRAGMENT_SHADER or GL_VERTEX_SHADER.
        # If the source fails to compile, retrieve the error message and raise ShaderError.
        # Store the compiled shader so we can delete it later on.
        shader = glCreateShader(type)
        status = c_int(-1)
        glShaderSource(shader, 1, cast(pointer(c_char_p(source)), POINTER(POINTER(c_char))), None)
        glCompileShader(shader)
        glGetShaderiv(shader, GL_COMPILE_STATUS, byref(status))
        if status.value == 0:
            raise self._error(shader, type=COMPILE)
        self._compiled.append(shader)
        return shader
        
    def _build(self):
        # Each Shader has its own OpenGL rendering program and you need to switch between them.
        # Compile fragment and vertex shaders and build the program.
        program = glCreateProgram()
        status  = c_int(-1)
        if self._vertex:
            glAttachShader(program, self._compile(self._vertex, GL_VERTEX_SHADER))
        if self._fragment:
            glAttachShader(program, self._compile(self._fragment, GL_FRAGMENT_SHADER))
        glLinkProgram(program)
        glGetProgramiv(program, GL_LINK_STATUS, byref(status))
        if status.value == 0:
            raise self._error(program, type=BUILD)
        self._program = program

    def _error(self, obj, type=COMPILE):
        # Get the info for the failed glCompileShader() or glLinkProgram(),
        # delete the failed shader or program,
        # return a ShaderError with the error message.
        f1 = type==COMPILE and glGetShaderiv      or glGetProgramiv
        f2 = type==COMPILE and glGetShaderInfoLog or glGetProgramInfoLog
        f3 = type==COMPILE and glDeleteShader     or glDeleteProgram
        length = c_int(); f1(obj, GL_INFO_LOG_LENGTH, byref(length))  
        msg = ""     
        if length.value > 0:
            msg = create_string_buffer(length.value); f2(obj, length, byref(length), msg)
            msg = msg.value
        f3(obj)
        return ShaderError(msg, type)

    def get(self, name):
        """ Returns the value of the variable with the given name.
        """
        return self.variables[name]

    def set(self, name, value):
        """ Set the value of the variable with the given name in the GLSL source script.
            Supported variable types are: vec2(), vec3(), vec4(), single int/float, list of int/float.
            Variables will be initialized when Shader.push() is called (i.e. glUseProgram).
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
            if next((v for v in value if isinstance(v, float))) is not None:
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
            ShaderError, "don't know how to handle variable %s" % value.__class__
    
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
        # pop() just removes any active program.
        if self._active == True:
            glUseProgram(0)
            self._active = False

    @property
    def active(self):
        return self._active
        
    @property
    def source(self):
        return (self._vertex, self._fragment)
    
    def __del__(self):
        try:
            for shader in self._compiled:
                if glDetachShader and self._program:
                    glDetachShader(self._program, shader)
                if glDeleteShader: 
                    glDeleteShader(shader)
            if glDeleteProgram: 
                glDeleteProgram(self._program)
        except:
            pass

class ShaderFacade:
    def __init__(self, vertex=None, fragment=None):
        # Acts like a shader but doesn't do anything.
        pass
    @property
    def variables(self):
        return {}
    @property
    def active(self):
        return None
    def get(self, name):
        return None
    def set(self, name, value):
        pass
    def push(self):
        pass
    def pop(self):
        pass

SUPPORTED = True # Graphics hardware supports shaders?

def shader(vertex=DEFAULT_VERTEX_SHADER, fragment=DEFAULT_FRAGMENT_SHADER, silent=True):
    """ Returns a compiled Shader from the given GLSL source code.
        With silent=True, never raises an error but instead returns a ShaderFacade.
        During startup, a number of Shaders are created.
        This mechanisms ensures that the module doesn't crash while doing this,
        instead the shader simply won't have any visible effect and SUPPORTED will be False.
    """
    if not silent:
        return Shader(vertex, fragment)
    try:
        return Shader(vertex, fragment)
    except Exception, e:
        SUPPORTED = False
        return ShaderFacade()

#=====================================================================================================

#--- FILTER ------------------------------------------------------------------------------------------
# Stores a shader's variables and applies them once push() is called.
# The shader is created only once for perfomance while filters can exist multiple times.
# Textures that are drawn between Filter.push() and Filter.pop() have the effect applied to them.

class Filter(object):
    
    def __init__(self):
        """ Filter combines a Shader with variable settings.
            Variables need to be prepared in Filter.push() before passing them to the shader:
            e.g. creating a list of kernel values, calculating a scale based on image height, ...
            Performance note: create the Shader separately, not during initialization.
        """
        # Shader and its variables need to be stored here.
        self.shader  = None
        self.texture = None
        
    def push(self):
        """ Installs the filter so it will be applied to the next image() call.
        """
        # Shader needs to set its variables here:
        # self.shader.set(variable, value)
        self.shader.push()
        
    def pop(self):
        """ Removes the filter.
        """
        self.shader.pop()

#=====================================================================================================

#--- INVERT -----------------------------------------------------------------------------------------

_invert = shader(fragment='''
uniform sampler2D src;
void main() {
    gl_FragColor = texture2D(src, gl_TexCoord[0].xy);
    gl_FragColor.rgb = 1.0 - gl_FragColor.rgb;
}''')

class Invert(Filter):
    
    def __init__(self, texture):
        self.shader  = _invert
        self.texture = texture
        
    def push(self):
        self.shader.push()

#--- GRADIENT ----------------------------------------------------------------------------------------

LINEAR = "linear"
RADIAL = "radial"

_gradient = {}
_gradient[LINEAR] = shader(fragment='''
uniform sampler2D src;
uniform vec4 clr1;
uniform vec4 clr2;
void main() {
    vec2 v = gl_TexCoord[0].xy;
    gl_FragColor = clr1 * v.y + clr2 * (1.0 - v.y);
}''')
_gradient[RADIAL] = shader(fragment='''
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
        self.shader  = _gradient[LINEAR]
        self.texture = texture
        self.clr1    = clr1
        self.clr2    = clr2
        
    def push(self):
        self.shader.set("clr1", self.clr1)
        self.shader.set("clr2", self.clr2)
        self.shader.push()

class RadialGradient(Filter):
    
    def __init__(self, texture, clr1=vec4(0,0,0,1), clr2=vec4(1,1,1,1)):
        self.shader  = _gradient[RADIAL]
        self.texture = texture
        self.clr1    = clr1
        self.clr2    = clr2
        
    def push(self):
        self.shader.set("clr1", self.clr1)
        self.shader.set("clr2", self.clr2)
        self.shader.push()

#--- COLORIZE ---------------------------------------------------------------------------------------

_colorize = shader(fragment='''
uniform sampler2D src;
uniform vec4 color;
uniform vec4 bias;
void main() {
    vec4 p = texture2D(src, gl_TexCoord[0].xy);
    gl_FragColor = clamp(p * color + bias, 0.0, 1.0);
}''')

class Colorize(Filter):
    
    def __init__(self, texture, color=vec4(1,1,1,1), bias=vec4(0,0,0,0)):
        self.shader  = _colorize
        self.texture = texture
        self.color   = color
        self.bias    = bias
        
    def push(self):
        self.shader.set("color", self.color)
        self.shader.set("bias",  self.bias)
        self.shader.push()

#--- COLORSPACE -------------------------------------------------------------------------------------
# Helper functions for conversion between RGB and HSB that we can use in other filters.
# Based on "Photoshop math with GLSL shaders" (2009), Romain Dura,
# http://blog.mouaif.org/?p=94

glsl_hsb2rgb = '''
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

glsl_rgb2hsb = '''
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
_adjustment[BRIGHTNESS] = shader(fragment='''
uniform sampler2D src;
uniform float m;
void main() {
    vec4 p = texture2D(src, gl_TexCoord[0].xy);
    gl_FragColor = vec4(clamp(p.rgb + m, 0.0, 1.0), p.a);
}''')
_adjustment[CONTRAST] = shader(fragment='''
uniform sampler2D src;
uniform float m;
void main() {
    vec4 p = texture2D(src, gl_TexCoord[0].xy);
    gl_FragColor = vec4(clamp((p.rgb - 0.5) * m + 0.5, 0.0, 1.0), p.a);
}''')
_adjustment[SATURATION] = shader(fragment='''
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
_adjustment[HUE] = shader(fragment=glsl_hsb2rgb+glsl_rgb2hsb+'''
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
        self.shader  = _adjustment[BRIGHTNESS]
        self.texture = texture
        self.m       = m
        
    def push(self):
        self.shader.set("m", float(self.m-1))
        self.shader.push()

class ContrastAdjustment(Filter):
    
    def __init__(self, texture, m=1.0):
        self.shader  = _adjustment[CONTRAST]
        self.texture = texture
        self.m       = m
        
    def push(self):
        self.shader.set("m", float(self.m))
        self.shader.push()

class SaturationAdjustment(Filter):
    
    def __init__(self, texture, m=1.0):
        self.shader  = _adjustment[SATURATION]
        self.texture = texture
        self.m       = m
        
    def push(self):
        self.shader.set("m", float(max(self.m, 0)))
        self.shader.push()

class HueAdjustment(Filter):
    
    def __init__(self, texture, m=0.0):
        self.shader  = _adjustment[HUE]
        self.texture = texture
        self.m       = m
        
    def push(self):
        self.shader.set("m", float(self.m));
        self.shader.push()

#--- BRIGHTPASS --------------------------------------------------------------------------------------
# Note: the magic numbers 0.2125, 0.7154, 0.0721 represent how (in RGB) 
# green contributes the most to luminosity while blue hardly contributes anything.
# Thus, luminance L = R*0.2125 + G*0.7154 + B+0.0721

_brightpass = shader(fragment='''
uniform sampler2D src;
uniform float threshold;
void main() {
    vec4 p = texture2D(src, gl_TexCoord[0].xy);
    float L = dot(p.rgb, vec3(0.2125, 0.7154, 0.0721)); // luminance
    gl_FragColor = (L > threshold)? vec4(p.rgb, p.a) : vec4(0.0, 0.0, 0.0, p.a);
}''')

class BrightPass(Filter):
    
    def __init__(self, texture, threshold=0.5):
        self.shader    = _brightpass
        self.texture   = texture
        self.threshold = threshold
        
    def push(self):
        self.shader.set("threshold", float(self.threshold));
        self.shader.push()

#--- BLUR --------------------------------------------------------------------------------------------
# Based on "Gaussian Blur Filter Shader" (2008), 
# http://www.gamerendering.com/2008/10/11/gaussian-blur-filter-shader/
# Blurring occurs in two steps (requiring an FBO): horizontal blur and vertical blur.
# Separating these two steps reduces the problem to linear complexity (i.e. it is faster).

glsl_blur = '''
uniform sampler2D src;
uniform int kernel;
uniform float radius;
uniform vec2 extent;
void main() {
    vec2 v = gl_TexCoord[0].xy;
    vec4 p = vec4(0.0);
    float n = float(kernel * kernel);
    if (v.x <= extent.x && v.y <= extent.y) {
        for (int i=1; i<kernel; i++) {
            float a = float(i) * radius;
            float b = float(kernel - i) / n;
            p += texture2D(src, vec2(v.x%s, v.y%s)) * b;
            p += texture2D(src, vec2(v.x%s, v.y%s)) * b;
        }
        p += texture2D(src, vec2(v.x, v.y)) * float(kernel) / n;
    }
    gl_FragColor = p;
}'''
_blur = {
    "horizontal": shader(fragment=glsl_blur % ("-a","","+a","")), # vary v.x
    "vertical"  : shader(fragment=glsl_blur % ("","-a","","+a"))  # vary v.y
}

class HorizontalBlur(Filter):
    
    def __init__(self, texture, kernel=9, scale=1.0):
        self.shader  = _blur["horizontal"]
        self.texture = texture
        self.kernel  = kernel
        self.scale   = scale
        
    def push(self):
        self.shader.set("kernel", int(self.kernel));
        self.shader.set("radius", float(self.scale) / self.texture.width)
        self.shader.set("extent", vec2(*extent2(self.texture)))
        self.shader.push()

class VerticalBlur(Filter):
    
    def __init__(self, texture, kernel=9, scale=1.0):
        self.shader  = _blur["vertical"]
        self.texture = texture
        self.kernel  = kernel
        self.scale   = scale
        
    def push(self):
        self.shader.set("kernel", int(self.kernel));
        self.shader.set("radius", float(self.scale) / self.texture.height)
        self.shader.set("extent", vec2(*extent2(self.texture)))
        self.shader.push()

# It is useful to have a blur in a single pass as well,
# which we can use as a parameter for the image() command.
# However, for a simple 3x3 in separate steps => 6 calculations, single pass => 9 calculations.
_blur["gaussian3x3"] = shader(fragment='''
uniform sampler2D src;
uniform vec2 radius;
void main() {
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
        self.shader = _blur["gaussian3x3"]
        self.texture = texture
        self.scale = scale
        
    def push(self):
        x = float(self.scale) / self.texture.width
        y = float(self.scale) / self.texture.height
        self.shader.set("radius", vec2(x, y))
        self.shader.push()

#--- COMPOSITING -------------------------------------------------------------------------------------

# Compositing function.
# It will be reused in alpha compositing and blending filters below.
# It prepares pixels p1 and p2, which need to be mixed into vec4 p.
glsl_compositing = '''
uniform sampler2D src1;
uniform sampler2D src2;
uniform vec2 extent;
uniform vec2 offset;
uniform vec2 ratio;
uniform float alpha;
void main() {
    vec2 v1 = gl_TexCoord[0].xy;
    vec2 v2 = v1 * ratio - offset * extent;
    vec4 p1 = texture2D(src1, v1.xy);
    vec4 p2 = texture2D(src2, v2.xy);
    if (v2.x < 0.0 || 
        v2.y < 0.0 || 
        v2.x > extent.x + 0.001 || 
        v2.y > extent.y + 0.001) { 
        gl_FragColor = p1; 
        return; 
    }
    vec4 p  = vec4(0.0);
    %s
    gl_FragColor = p; 
}'''

class Compositing(Filter):
    
    def __init__(self, shader, texture, blend, alpha=1.0, dx=0, dy=0):
        """ A filter that mixes a base image (the destination) with a blend image (the source).
            Used to implement alpha compositing and blend modes.
            - dx: the horizontal offset (in pixels) of the blend layer.
            - dy: the vertical offset (in pixels) of the blend layer.
        """
        self.shader  = shader
        self.texture = texture
        self.blend   = blend
        self.alpha   = alpha   
        self.dx      = dx
        self.dy      = dy 

    def push(self):
        w  = float(self.blend.width)
        h  = float(self.blend.height)
        w2 = float(ceil2(w))
        h2 = float(ceil2(h))
        dx = float(self.dx) / w
        dy = float(self.dy) / h
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(self.texture.target, self.texture.id)        
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(self.blend.target, self.blend.id)
        glActiveTexture(GL_TEXTURE0)
        self.shader.set("src1", 0)
        self.shader.set("src2", 1)
        self.shader.set("extent", vec2(w/w2, h/h2)) # Blend extent.
        self.shader.set("offset", vec2(dx, dy))     # Blend offset.
        self.shader.set("ratio", vec2(*ratio2(self.texture, self.blend))) # Image-blend proportion.
        self.shader.set("alpha", self.alpha)
        self.shader.push()

#--- ALPHA TRANSPARENCY ------------------------------------------------------------------------------

_alpha = {}
_alpha["transparency"] = shader(fragment='''
uniform sampler2D src;
uniform float alpha;
void main() {
    vec4 p = texture2D(src, gl_TexCoord[0].xy);
    gl_FragColor = vec4(p.rgb, p.a * alpha);
}''')
_alpha["mask"] = shader(fragment=glsl_compositing % '''
    p = vec4(p1.rgb, p1.a * (p2.r * p2.a * alpha));
'''.strip())

class AlphaTransparency(Filter):

    def __init__(self, texture, alpha=1.0):
        self.shader  = _alpha["transparency"]
        self.texture = texture
        self.alpha   = alpha
        
    def push(self):
        self.shader.set("alpha", float(max(0, min(1, self.alpha))))
        self.shader.push()

class AlphaMask(Compositing):

    def __init__(self, texture, blend, alpha=1.0, dx=0, dy=0):
        Compositing.__init__(self, _alpha["mask"], texture, blend, alpha, dx, dy)
        self.shader = _alpha["mask"]

#--- BLEND MODES -------------------------------------------------------------------------------------
# Based on "Photoshop math with GLSL shaders" (2009), Romain Dura,
# http://blog.mouaif.org/?p=94

ADD       = "add"       # Pixels are added.
SUBTRACT  = "subtract"  # Pixels are subtracted.
LIGHTEN   = "lighten"   # Lightest value for each pixel.
DARKEN    = "darken"    # Darkest value for each pixel.
MULTIPLY  = "multiply"  # Pixels are multiplied, resulting in a darker image.
SCREEN    = "screen"    # Pixels are inverted/multiplied/inverted, resulting in a brighter picture.
OVERLAY   = "overlay"   # Combines multiply and screen: light parts become ligher, dark parts darker.
HARDLIGHT = "hardlight" # Same as overlay, but uses the blend instead of base image for luminance.
HUE       = "hue"       # Hue from the blend image, brightness and saturation from the base image.

# If the blend is opaque (alpha=1.0), swap base and blend.
# This way lighten, darken, multiply and screen appear the same as in Photoshop and Core Image.
_blendx = '''if (p2.a == 1.0) { vec4 p3=p1; p1=p2; p2=p3; }
    '''
# Blending operates on RGB values, the A needs to be handled separately.
# Where both images are transparent, their transparency is blended.
# Where the base image is fully transparent, the blend image appears source over.
# There is a subtle transition at transparent edges, which makes the edges less jagged.
glsl_blend = glsl_compositing % '''
    vec3 w  = vec3(1.0); // white
    %s
    p = mix(p1, clamp(p, 0.0, 1.0), p2.a * alpha);
    p = (v1.x * ratio.x > 1.0 || v1.y * ratio.y > 1.0)? p1 : p;
    p = (p1.a < 0.25)? p * p1.a + p2 * (1.0-p1.a) : p;
'''.strip()
_blend = {}
_blend[ADD]      =           'p = vec4(p1.rgb + p2.rgb, 1.0);'
_blend[SUBTRACT] =           'p = vec4(p1.rgb + p2.rgb - 1.0, 1.0);'
_blend[LIGHTEN]  = _blendx + 'p = vec4(max(p1.rgb, p2.rgb), 1.0);'
_blend[DARKEN]   = _blendx + 'p = vec4(min(p1.rgb, p2.rgb), 1.0);'
_blend[MULTIPLY] = _blendx + 'p = vec4(p1.rgb * p2.rgb, 1.0);'
_blend[SCREEN]   = _blendx + 'p = vec4(w - (w - p1.rgb) * (w - p2.rgb), 1.0);'
_blend[OVERLAY]  = '''
    float L = dot(p1.rgb, vec3(0.2125, 0.7154, 0.0721)); // luminance
    vec4 a = vec4(2.0 * p1.rgb * p2.rgb, 1.0);
    vec4 b = vec4(w - 2.0 * (w - p1.rgb) * (w - p2.rgb), 1.0);
    p = (L < 0.45)? a : (L > 0.55)? b : vec4(mix(a.rgb, b.rgb, (L - 0.45) * 10.0), 1.0);
'''
_blend[HARDLIGHT] = _blend[OVERLAY].replace("dot(p1", "dot(p2")
_blend[HUE] = '''
    vec3 h1 = rgb2hsb(p1.rgb);
    vec3 h2 = rgb2hsb(p2.rgb);
    p = vec4(hsb2rgb(vec3(h2.x, h1.yz)).rgb, p1.a);
'''

for f in _blend.keys():
    src = glsl_blend % _blend[f].strip()
    src = f==HUE and glsl_rgb2hsb + glsl_hsb2rgb + src or src # Hue blend requires rgb2hsb() function.
    _blend[f] = shader(fragment=src)

class Blend(Compositing):
    
    def __init__(self, mode, texture, blend, alpha=1.0, dx=0, dy=0):
        Compositing.__init__(self, _blend[mode], texture, blend, alpha, dx, dy)

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
# - vec2 offset: horizontal and vertical offset from the image center (-0.5 to +0.5).
# - vec2 extent: the actual size of the image (0.0-1.0) in the texture.
#   Textures have a size power of 2 (512, 1024, ...) but the actual image may be smaller.
#   We need to know the extent of the image in the texture to calculate its center.
# - float ratio: the ratio between width and height, so the effect doesn't get stretched.
# - float m: the magnitude of the effect (e.g. radius, ...) 
# - float i: the intensity of the effect (e.g. number of rotations, ...) 
# - vec2 n: a normalized texture space between -1.0 and 1.0 (instead of 0.0-1.0).
glsl_distortion = '''
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
    %s
    gl_FragColor = p; 
}'''
# Polar coordinates.
# Most of the effects are based on simple angle and radius transformations.
# After the transformations, convert back to cartesian coordinates n.
glsl_polar = '''
    float r = length(n);
    float phi = atan(n.y, n.x);
    %s
    n = vec2(r*cos(phi), r*sin(phi));
'''.strip()
# For most effects, pixels are not wrapped around the edges.
# The second version wraps, with respect to the extent of the actual image in its power-of-2 texture.
# The third version wraps with a flipped image (transition).
glsl_wrap = (
    '''vec4 p = (v.x < 0.0 || v.y < 0.0 || v.x > 0.999 || v.y > 0.999)? vec4(0.0) : texture2D(src, v);''',
    '''
    v.x = (v.x >= extent.x - 0.001)? mod(v.x, extent.x) - 0.002 : max(v.x, 0.001);
    v.y = (v.y >= extent.y - 0.001)? mod(v.x, extent.x) - 0.002 : max(v.y, 0.001);
    vec4 p = texture2D(src, v);'''.strip(),
    '''
    v.x = (v.x >= extent.x - 0.001)? (extent.x - (v.x-extent.x)) - 0.002 : max(v.x, 0.001);
    v.y = (v.y >= extent.y - 0.001)? (extent.y - (v.y-extent.y)) - 0.002 : max(v.y, 0.001);
    vec4 p = texture2D(src, v);'''.strip())

_distortion = {}
_distortion[BUMP]    = 'r = r * smoothstep(i, m, r);'
_distortion[DENT]    = 'r = 2.0 * r - r * smoothstep(0.0, m, r/i);'
_distortion[PINCH]   = 'r = pow(r, m/i) * m;'
_distortion[FISHEYE] = 'r = r * r / sqrt(2.0);'
_distortion[SPLASH]  = 'if (r > m) r = m;'
_distortion[TWIRL]   = 'phi = phi + (1.0 - smoothstep(-m, m, r)) * i;'
_distortion[MIRROR]  = '''
    if (m > 0.0) { n.x += offset.x * extent.x * ratio; n.x = n.x * sign(n.x); }
    if (i > 0.0) { n.y += offset.y * extent.y;         n.y = n.y * sign(n.y); }
'''.strip()
_distortion[STRETCH] = '''
    vec2 s = sign(n);
    n = abs(n);
    n = (1.0-i) * n + i * smoothstep(m*0.25, m, n) * n;
    n = s * n;
'''.strip()

for f in (BUMP, DENT, PINCH, FISHEYE, SPLASH, TWIRL):
    _distortion[f] = shader(fragment=glsl_distortion % (glsl_polar % _distortion[f], glsl_wrap[0]))
for f in (STRETCH, MIRROR):
    _distortion[f] = shader(fragment=glsl_distortion % (             _distortion[f], glsl_wrap[2]))

class Distortion(Filter):
    
    def __init__(self, effect, texture, dx=0, dy=0, m=1.0, i=1.0):
        """ Distortion filter with dx, dy offset from the center (between -0.5 and 0.5),
            magnitude m as the radius of effect, intensity i as the depth of the effect.
        """
        self.shader  = _distortion[effect]
        self.texture = texture
        self.dx      = dx
        self.dy      = dy
        self.m       = m
        self.i       = i
    
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
        self.shader.set("extent", vec2(w/w2, h/h2))
        self.shader.set("offset", vec2(float(2*self.dx), float(2*self.dy)))
        self.shader.set("ratio", w2/h2)
        self.shader.set("m", float(self.m))
        self.shader.set("i", float(self.i))
        self.shader.push()

#=====================================================================================================

#--- FRAME BUFFER OBJECT -----------------------------------------------------------------------------
# Based on "Frame Buffer Object 101" (2006), Rob Jones, 
# http://www.gamedev.net/reference/articles/article2331.asp

_UID = 0
def _uid():
    # Each FBO has a unique ID.
    global _UID; _UID+=1; return _UID;
    
def _texture(width, height):
    # Returns an empty texture of the given width and height.
    return Texture.create(width, height)

def glCurrentViewport(x=None, y=None, width=None, height=None):
    """ Returns a (x, y, width, height)-tuple with the current viewport bounds.
        If x, y, width and height are given, set the viewport bounds.
    """
    # Why? To switch between the size of the onscreen canvas and the offscreen buffer.
    # The canvas could be 256x256 while an offscreen buffer could be 1024x1024.
    # Without switching the viewport, information from the buffer would be lost.
    if x is not None and y is not None and width is not None and height is not None:
        glViewport(x, y, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(x, width, y, height, -1, 1)
        glMatrixMode(GL_MODELVIEW)
    xywh = (GLint*4)(); glGetIntegerv(GL_VIEWPORT, xywh)
    return tuple(xywh)

# The FBO stack keeps track of nested FBO's.
# When OffscreenBuffer.pop() is called, we revert to the previous buffer.
# Usually, this is the onscreen canvas, but in a render() function that contains
# filters or nested render() calls, this is the previous FBO.
_FBO_STACK = []

class OffscreenBufferError(Exception):
    pass

class OffscreenBuffer(object):
    
    def __init__(self, width, height):
        """ "FBO" is an OpenGL extension to do "Render to Texture", drawing in an offscreen buffer.
            It is useful as a place to chain multiple shaders,
            since each shader has its own program and we can only install one program at a time.
        """
        self.id = c_uint(_uid())
        try: glGenFramebuffersEXT(1, byref(self.id))
        except:
            raise OffscreenBufferError, "offscreen buffer not supported."
        self.texture   = None
        self._viewport = (None, None, None, None) # The canvas bounds, set in OffscreenBuffer.push().
        self._active   = False
        self._init(width, height)
        #self._init_depthbuffer()
        
    def _init(self, width, height):
        self.texture = _texture(int(width), int(height))  

    @property
    def width(self):
        return self.texture.width
    
    @property
    def height(self):
        return self.texture.height
    
    @property
    def active(self):
        return self._active
    
    def push(self):
        """ Between push() and pop(), all drawing is done offscreen in OffscreenBuffer.texture.
            The offscreen buffer has its own transformation state,
            so any translate(), rotate() etc. does not affect the onscreen canvas.
        """
        _FBO_STACK.append(self)
        glBindTexture(self.texture.target, self.texture.id)
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, self.id.value)      
        glFramebufferTexture2DEXT(
            GL_FRAMEBUFFER_EXT, 
            GL_COLOR_ATTACHMENT0_EXT, 
            self.texture.target, 
            self.texture.id, 
            self.texture.level
        )
        # FBO's can fail when not supported by the graphics hardware,
        # or when supplied an image of size 0 or unequal width/height.
        # Check after glBindFramebufferEXT() and glFramebufferTexture2DEXT().
        if glCheckFramebufferStatusEXT(GL_FRAMEBUFFER_EXT) != GL_FRAMEBUFFER_COMPLETE_EXT:
            msg = self.texture.width == self.texture.height == 0 and "width=0, height=0." or ""
            raise OffscreenBufferError, msg            
        # Separate the offscreen from the onscreen transform state.
        # Separate the offscreen from the onscreen canvas size.
        self._viewport = glCurrentViewport()
        glPushMatrix()
        glLoadIdentity()
        glCurrentViewport(0, 0, self.texture.width, self.texture.height)
        glColor4f(1.0,1.0,1.0,1.0)
        # FBO's work with a simple GL_LINE_SMOOTH anti-aliasing.
        # The instructions on how to enable framebuffer multisampling are pretty clear:
        # (http://www.opengl.org/wiki/GL_EXT_framebuffer_multisample)
        # but glRenderbufferStorageMultisampleEXT doesn't appear to work (yet),
        # plus there is a performance drop.
        glEnable(GL_LINE_SMOOTH)
        # Blending transparent images in a transparent FBO is a bit tricky
        # because alpha is premultiplied, an image with 50% transparency
        # will come out 25% transparency with glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA).
        # http://www.opengl.org/discussion_boards/ubbthreads.php?ubb=showflat&Number=257630
        # http://www.openframeworks.cc/forum/viewtopic.php?f=9&t=2215
        # This blend mode gives better results:
        glEnable(GL_BLEND)
        glBlendFuncSeparate(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_ONE, GL_ONE_MINUS_SRC_ALPHA)
        self._active = True
    
    def pop(self):
        """ Reverts to the onscreen canvas. 
            The contents of the offscreen buffer can be retrieved with OffscreenBuffer.texture.
        """
        # Switch to onscreen canvas size and transformation state.
        # Switch to onscreen canvas.
        # Reset to the normal blending mode.
        _FBO_STACK.pop(-1)
        glCurrentViewport(*self._viewport)
        glPopMatrix()
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, _FBO_STACK and _FBO_STACK[-1].id or 0)
        glBlendFuncSeparate(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_ONE, GL_ONE_MINUS_SRC_ALPHA)
        #glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self._active = False
    
    def render(self):
        """ Executes the drawing commands in OffscreenBuffer.draw() offscreen and returns image.
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
        return self.texture.get_region(x, y, width, height) 

    def reset(self, width=None, height=None):
        """ Resizes the offscreen buffer by attaching a new texture to it.
            This will destroy the contents of the previous buffer.
            If you do not explicitly reset the buffer, the contents from previous drawing
            between OffscreenBuffer.push() and OffscreenBuffer.pop() is retained.
        """
        if self._active:
            raise OffscreenBufferError, "can't reset offscreen buffer when active"
        if width is None:
            width = self.width
        if height is None:
            height = self.height
        self._init(width, height)
        
    def clear(self):
        glClear(GL_COLOR_BUFFER_BIT)
        glClear(GL_DEPTH_BUFFER_BIT)
        glClear(GL_STENCIL_BUFFER_BIT)

    def _init_depthbuffer(self):
        self._depthbuffer = c_uint(_uid())
        glGenRenderbuffersEXT(1, byref(self._depthbuffer))
        glBindRenderbufferEXT(GL_RENDERBUFFER_EXT, self._depthbuffer)
        glRenderbufferStorageEXT(GL_RENDERBUFFER_EXT, GL_DEPTH_COMPONENT, self.width, self.height)
        glFramebufferRenderbufferEXT(
            GL_FRAMEBUFFER_EXT,
            GL_DEPTH_ATTACHMENT_EXT,
            GL_RENDERBUFFER_EXT,
            self._depthbuffer
        )
    
    def __del__(self):
        try:
            if glDeleteFramebuffersEXT:
                glDeleteFramebuffersEXT(1, self.id)
            if glDeleteRenderbuffersEXT and hasattr(self, "_depthbuffer"):
                glDeleteRenderbuffersEXT(1, self._depthbuffer)
        except:
            pass

FBO = OffscreenBuffer

#=====================================================================================================

#--- OFFSCREEN RENDERING -----------------------------------------------------------------------------
# Uses an offscreen buffer to render filters and drawing commands to images.

try: 
    _buffer = OffscreenBuffer(640, 480)
except OffscreenBufferError:
    _buffer = None

def filter(img, filter=None, clear=True):
    """ Returns a new Image object with the given filter applied to it.
        - img   : an image that can be passed to the image() command.
        - filter: an instance of the Filter class, with parameters set.
        - clear : if True, clears the contents of the offscreen buffer and resizes it to the image.
    """
    # For file paths, textures and Pixel objects, create an Image first.
    if not isinstance(img, Image):
        img = Image(img)
    # Reuse main _buffer when possible, otherwise create one on the fly
    # (this will be necessary when filter() or render() is nested inside render()).
    if not _buffer or _buffer.active:
        buffer = OffscreenBuffer(img.texture.width, img.texture.height)
    elif clear:
        buffer = _buffer
        buffer.reset(img.texture.width, img.texture.height)
    else:
        buffer = _buffer
    buffer.push()
    if filter != None:
        filter.texture = img.texture # Register the current texture with the filter.
        filter.push()
    # This blend mode gives better results for transparent images:
    glBlendFuncSeparate(GL_ONE, GL_ONE_MINUS_SRC_ALPHA, GL_ONE, GL_ONE_MINUS_SRC_ALPHA)
    # Note: Image.alpha and Image.color attributes won't work here,
    # because the shader overrides the default drawing behavior.
    # Instead, add the transparent() and colorize() filters to the chain.
    img.draw(0, 0, img.texture.width, img.texture.height)
    if filter != None:
        filter.pop()
    buffer.pop()
    return img.copy(texture=buffer.texture)

class RenderedImage(Image):
    
    def draw(self, *args, **kwargs):
        # Textures rendered in the FBO look slightly washed out.
        # The render() command yields a RenderedImage object,
        # which draw() method uses a blending trick to correct the colors:
        glBlendFunc(GL_ONE, GL_ONE_MINUS_SRC_ALPHA)
        Image.draw(self, *args, **kwargs)
        glBlendFuncSeparate(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_ONE, GL_ONE_MINUS_SRC_ALPHA)
    
    def save(self, path):
        # XXX Colors will appear washed out in the exported image.
        Image.save(self, path)
    
def render(function, width, height, clear=True, **kwargs):
    """ Returns an Image object from a function containing drawing commands (i.e. a procedural image).
        This is useful when, for example, you need to render filters on paths.
        - function: a function containing drawing commands.
        - width   : width of the offscreen canvas.
        - height  : height of the offscreen canvas.
        - clear   : when False, retains the contents of the offscreen canvas, without resizing it.
    """
    # Reuse main _buffer when possible, otherwise create one on the fly
    # (this will be necessary when render() is nested inside another render()).
    if not _buffer or _buffer.active:
        buffer = OffscreenBuffer(width, height)
    elif clear:
        buffer = _buffer
        buffer.reset(width, height)
    else:
        buffer = _buffer
    buffer.push()
    function(**kwargs)
    buffer.pop()
    return RenderedImage(buffer.texture)
    
#--- OFFSCREEN FILTERS -------------------------------------------------------------------------------
# Images are rendered offscreen with the filter applied, and the new image returned.

def invert(img):
    """ Returns an image with inverted colors (e.g. white becomes black).
    """
    return filter(img, Invert(img.texture))

def solid(width, height, fill=(0,0,0,0)):
    """ Generates an image filled with a solid color.
    """
    clr = tuple([int(v*255) for v in fill])
    return Image(SolidColorImagePattern(clr).create_image(width, height).get_texture())

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
    img = filter(img, f(img.texture, vec4(*clr1), vec4(*clr2)))
    # Reuse main _buffer when possible, otherwise create one on the fly
    # (this will be necessary when filter() or render() is nested inside render()).
    if not _buffer or _buffer.active:
        buffer = OffscreenBuffer(img.texture.width, img.texture.height)
    else:
        buffer = _buffer
    # If the given dimensions are not power of 2,
    # scale down the gradient to the given dimensions.
    if width != img.width or height != img.height:
        buffer.reset(width, height)
        buffer.push()
        img.width  = width
        img.height = height
        img.draw()
        buffer.pop()
        return img.copy(texture=buffer.texture)
    return img

def colorize(img, color=(1,1,1,1), bias=(0,0,0,0)):
    """ Applies a colorize filter to the image and returns the colorized image.
        - color: a Color (or a tuple) of RGBA-values to multiply with each image pixel.
        - bias : a Color (or a tuple) of RGBA-values to add to each image pixel.
    """
    return filter(img, Colorize(img.texture, vec4(*color), vec4(*bias)))

def adjust(img, brightness=1.0, contrast=1.0, saturation=1.0, hue=0.0):
    """ Applies color adjustment filters to the image and returns the adjusted image.
        - brightness: the overall lightness or darkness (0.0 is a black image).
        - contrast  : the difference in brightness between regions.
        - saturation: the intensity of the colors (0.0 is a grayscale image).
        - hue       : the shift in hue (1.0 is 360 degrees on the color wheel).
    """
    if brightness != 1: img = filter(img, BrightnessAdjustment(img.texture, brightness))
    if contrast   != 1: img = filter(img, ContrastAdjustment(img.texture, contrast))
    if saturation != 1: img = filter(img, SaturationAdjustment(img.texture, saturation))
    if hue        != 0: img = filter(img, HueAdjustment(img.texture, hue))
    return img
    
def desaturate(img):
    """ Returns a grayscale version of the image.
    """
    return filter(img, SaturationAdjustment(img.texture, 0.0))
    
grayscale = desaturate

def brightpass(img, threshold=0.3):
    """ Applies a bright pass filter, where pixels whose luminance falls below the threshold are black.
    """
    return filter(img, BrightPass(img.texture, threshold))

def blur(img, kernel=5, scale=1.0, amount=1, cumulative=False):
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
        img = filter(img, HorizontalBlur(img.texture, kernel, scale), clear=clear)
        img = filter(img, VerticalBlur(img.texture, kernel, scale), clear=clear)
    return img

def transparent(img, alpha=1.0):
    """ Returns a transparent version of the image.
        - alpha: the percentage of the original opacity of the image (0.0-1.0).
    """
    return filter(img, AlphaTransparency(img.texture, alpha))

def _q(img):
    # For images functioning as masks or blend layers,
    # apply any quad distortian and then use the texture of the distored image.
    if img.quad != (0,0,0,0,0,0,0,0):
        return filter(img)
    return img

def mask(img1, img2, alpha=1.0, dx=0, dy=0):
    """ Applies the second image as an alpha mask to the first image.
        The second image must be a grayscale image, where the black areas
        make the first image transparent (e.g. punch holes in it).
        - dx: horizontal offset (in pixels) of the alpha mask.
        - dy: vertical offset (in pixels) of the alpha mask.
    """
    return filter(img1, AlphaMask(img1.texture, _q(img2).texture, alpha, dx, dy))

def blend(img1, img2, mode=OVERLAY, alpha=1.0, dx=0, dy=0):
    """ Applies the second image as a blend layer with the first image.
        - dx: horizontal offset (in pixels) of the blend layer.
        - dy: vertical offset (in pixels) of the blend layer.
    """
    return filter(img1, Blend(mode, img1.texture, _q(img2).texture, alpha, dx, dy))

def add(img1, img2, alpha=1.0, dx=0, dy=0):
    return filter(img1, Blend(ADD, img1.texture, _q(img2).texture, alpha, dx, dy))

def subtract(img1, img2, alpha=1.0, dx=0, dy=0):
    return filter(img1, Blend(SUBTRACT, img1.texture, _q(img2).texture, alpha, dx, dy))

def lighten(img1, img2, alpha=1.0, dx=0, dy=0):
    return filter(img1, Blend(LIGHTEN, img1.texture, _q(img2).texture, alpha, dx, dy))
    
def darken(img1, img2, alpha=1.0, dx=0, dy=0):
    return filter(img1, Blend(DARKEN, img1.texture, _q(img2).texture, alpha, dx, dy))

def multiply(img1, img2, alpha=1.0, dx=0, dy=0):
    return filter(img1, Blend(MULTIPLY, img1.texture, _q(img2).texture, alpha, dx, dy))
    
def screen(img1, img2, alpha=1.0, dx=0, dy=0):
    return filter(img1, Blend(SCREEN, img1.texture, _q(img2).texture, alpha, dx, dy))
    
def overlay(img1, img2, alpha=1.0, dx=0, dy=0):
    return filter(img1, Blend(OVERLAY, img1.texture, _q(img2).texture, alpha, dx, dy))

def hardlight(img1, img2, alpha=1.0, dx=0, dy=0):
    return filter(img1, Blend(HARDLIGHT, img1.texture, _q(img2).texture, alpha, dx, dy))
    
def hue(img1, img2, alpha=1.0, dx=0, dy=0):
    return filter(img1, Blend(HUE, img1.texture, _q(img2).texture, alpha, dx, dy))
    
def glow(img, intensity=0.5, amount=1):
    """ Returns the image blended with a blurred version, yielding a glowing effect.
        - intensity: the opacity of the blur (0.0-1.0).
        - amount   : the number of times to blur. 
    """
    b = blur(img, kernel=9, scale=1.0, amount=max(1, amount))
    return add(img, b, alpha=intensity)

def bloom(img, intensity=0.5, amount=1, threshold=0.3):
    """ Returns the image blended with a blurred brightpass version, yielding a "magic glow" effect.
        - intensity: the opacity of the blur (0.0-1.0).
        - amount   : the number of times to blur.
        - threshold: the luminance threshold of pixels that light up.
    """
    b = brightpass(img, threshold)
    b = blur(img, kernel=9, scale=1.0, amount=max(1, amount))
    return add(img, b, alpha=intensity)

def distortion_mixin(type, dx, dy, **kwargs):
    # Each distortion filter has specific parameters to tweak the effect (usually radius and zoom).
    # Returns the magnitude m and intensity i from the keyword arguments,
    # which are the parameters expected by the Distortion Filter class.
    if type == BUMP:
        m = kwargs.get("radius", 0.5)
        i = lerp(-m*20, m*0.25, max(0, kwargs.get("zoom", 0.5))**0.1)
    elif type == DENT:
        m = max(0, 2 * kwargs.get("radius", 0.5))
        i = max(0, 1 * kwargs.get("zoom", 0.5))
    elif type == PINCH:
        m = 1.0
        i = max(0.2, 2 * kwargs.get("zoom", 0.75))
    elif type == TWIRL:
        m = kwargs.get("radius", 1.0)
        i = radians(kwargs.get("angle", 180.0))
    elif type == SPLASH:
        m = kwargs.get("radius", 0.5)
        i = 0
    elif type == MIRROR:
        m = int(kwargs.get("horizontal", True))
        i = int(kwargs.get("vertical", True))
        dx = clamp(dx, -0.5, 1.5)
        dy = clamp(dy, -0.5, 1.5)
    elif type == STRETCH:
        m = max(0, kwargs.get("radius", 0.5))
        i = max(0, min(1, 0.5 * kwargs.get("zoom", 1.0)))
    else:
        m = 0.5
        i = 0.5
    return dx, dy, m, i

#def bump(img, dx=0.5, dy=0.5, radius=0.5, zoom=0.5)
def bump(img, dx=0.5, dy=0.5, **kwargs):
    """ Returns the image with a bump distortion applied to it.
        - dx: horizontal origin of the effect, between 0.0 and 1.0.
        - dy: vertical origin of the effect, between 0.0 and 1.0.
        - radius: the radius of the affected area, proportional to the image size.
        - zoom: the amount to zoom in.
    """
    dx, dy, m, i = distortion_mixin(BUMP, dx, dy, **kwargs)
    return filter(img, filter=Distortion(BUMP, img.texture, dx-0.5, dy-0.5, m, i))

#def dent(img, dx=0.5, dy=0.5, radius=0.5, zoom=0.5)    
def dent(img, dx=0.5, dy=0.5, **kwargs):
    """ Returns the image with a dent distortion applied to it.
        - dx: horizontal origin of the effect, between 0.0 and 1.0.
        - dy: vertical origin of the effect, between 0.0 and 1.0.
        - radius: the radius of the affected area, proportional to the image size.
        - zoom: the amount to zoom in.
    """
    dx, dy, m, i = distortion_mixin(DENT, dx, dy, **kwargs)
    return filter(img, filter=Distortion(DENT, img.texture, dx-0.5, dy-0.5, m, i))

#def pinch(img, dx=0.5, dy=0.5, zoom=0.75)
def pinch(img, dx=0.5, dy=0.5, **kwargs):
    """ Returns the image with a pinch distortion applied to it.
        - dx: horizontal origin of the effect, between 0.0 and 1.0.
        - dy: vertical origin of the effect, between 0.0 and 1.0.
        - zoom: the amount of bulge (0.1-0.5) or pinch (0.5-1.0):
    """
    dx, dy, m, i = distortion_mixin(PINCH, dx, dy, **kwargs)
    return filter(img, filter=Distortion(PINCH, img.texture, dx-0.5, dy-0.5, m, i))

#def twirl(img, dx=0.5, dy=0.5, radius=1.0, angle=180.0)
def twirl(img, dx=0.5, dy=0.5, **kwargs):
    """ Returns the image with a twirl distortion applied to it.
        - dx: horizontal origin of the effect, between 0.0 and 1.0.
        - dy: vertical origin of the effect, between 0.0 and 1.0.
        - radius: the radius of the effect, proportional to the image size.
        - angle: the amount of rotation in degrees.
    """
    dx, dy, m, i = distortion_mixin(TWIRL, dx, dy, **kwargs)
    return filter(img, filter=Distortion(TWIRL, img.texture, dx-0.5, dy-0.5, m, i))

#def splash(img, dx=0.5, dy=0.5, radius=0.5)
def splash(img, dx=0.5, dy=0.5, **kwargs):
    """ Returns the image with a light-tunnel distortion applied to it.
        - dx: horizontal origin of the effect, between 0.0 and 1.0.
        - dy: vertical origin of the effect, between 0.0 and 1.0.
        - radius: the radius of the unaffected area, proportional to the image size.
    """
    dx, dy, m, i = distortion_mixin(SPLASH, dx, dy, **kwargs)
    return filter(img, filter=Distortion(SPLASH, img.texture, dx-0.5, dy-0.5, m, i))

#def stretch(img, dx=0.5, dy=0.5, radius=0.5, zoom=1.0)
def stretch(img, dx=0.5, dy=0.5, **kwargs):
    """ Returns the image with a zoom box distortion applied to it.
        - dx: horizontal origin of the effect, between 0.0 and 1.0.
        - dy: vertical origin of the effect, between 0.0 and 1.0.
        - radius: the radius of the affected area, proportional to the image size.
        - zoom: the amount to zoom in (0.0-2.0, where 1.0 means 1x zoomed in, or 200%).
    """
    dx, dy, m, i = distortion_mixin(STRETCH, dx, dy, **kwargs)
    return filter(img, filter=Distortion(STRETCH, img.texture, dx-0.5, dy-0.5, m, i))

#def mirror(img, dx=0.5, dy=0.5, horizontal=True, vertical=True)
def mirror(img, dx=0.5, dy=0.5, **kwargs):
    """ Returns the image mirrored along horizontal axis dx and vertical axis dy.
        - dx: horizontal origin of the effect, between 0.0 and 1.0.
        - dy: vertical origin of the effect, between 0.0 and 1.0.
        - horizontal: when True, mirrors the image horizontally.
        - vertical  : when True, mirrors the image vertically.
    """
    dx, dy, m, i = distortion_mixin(MIRROR, dx, dy, **kwargs)
    return filter(img, filter=Distortion(MIRROR, img.texture, dx-0.5, dy-0.5, m, i))

def dropshadow(img, alpha=0.5, amount=2, kernel=5):
    """ Returns a blurred and grayscale version of the image.
        If filters are not supported, returns a grayscale version without blur (using Image.color).
    """
    if not SUPPORTED:
        t = texture(img)
    else:
        t = blur(img, kernel=kernel, amount=amount).texture
    img = isinstance(img, Image) and img.copy(t) or Image(t)
    img.color.rgba = (0,0,0, alpha)
    return img

#--- ONSCREEN FILTERS --------------------------------------------------------------------------------
# These can be used directly as filter parameter for the image() command.
# This may be faster because no offscreen buffer is used to render the effect.

def inverted():
    return Invert(None)

def colorized(color=(1,1,1,1), bias=(0,0,0,0)):
    return Colorize(None, vec4(*color), vec4(*bias))
        
def adjusted(mode, v):
    if mode == BRIGHTNESS: 
        return BrightnessAdjustment(None, v)
    if mode == CONTRAST:
        return ContrastAdjustment(None, v)
    if mode == SATURATION:
        return SaturationAdjustment(None, v)
    if mode == HUE:
        return HueAdjustment(None, v)
    
def desaturated():
    return SaturationAdjustment(None, 0.0)
    
def blurred(scale=1.0):
    return Gaussian3x3Blur(None, scale)

def masked(img, alpha=1.0, dx=0, dy=0):
    return AlphaMask(None, _q(img).texture, alpha, dx, dy)

def blended(mode, img, alpha=1.0, dx=0, dy=0):
    return Blend(mode, None, _q(img).texture, alpha, dx, dy)
    
def distorted(type, dx=0.5, dy=0.5, **kwargs):
    dx, dy, m, i = distortion_mixin(type, dx, dy, **kwargs)
    return Distortion(type, None, dx-0.5, dy-0.5, m, i)