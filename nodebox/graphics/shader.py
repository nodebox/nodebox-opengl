# Fragment shaders, filters, Frame Buffer Object (FBO)
# Authors: Frederik De Bleser, Tom De Smedt
# License: GPL (see LICENSE.txt for details).
# Copyright (c) 2008 City In A Bottle (cityinabottle.org)

from pyglet.gl import *

#=====================================================================================================

def find(f, seq):
    """ Return first item in sequence where f(item) == True.
    """
    for item in seq:
        if f(item): 
            return item

pow2 = [2**n for n in range(20)]
def ceil2(x):
    """ Returns the nearest power of 2 that is higher than x, e.g. 700 => 1024.
    """
    for y in pow2:
        if y >= x:
            return y

#=====================================================================================================

#--- FRAGMENT SHADER ---------------------------------------------------------------------------------
# A fragment shader is a pixel effect (motion blur, fog, glow) executed on the GPU.
# http://www.lighthouse3d.com/opengl/glsl/index.php?fragmentp
# Fragment shaders are written in GLSL and expect their variables to be set from glUniform() calls.
# The FragmentShader class compiles the source code and has an easy way to set variables in the source.
# e.g. shader = FragmentShader(open("colorize.frag").read())
#      shader.set("color", vec4(1, 0.8, 1, 1))
#      shader.push()
#      image("box.png", 0, 0)
#      shader.pop()

def vec2(f1, f2)         : return (f1, f2)
def vec3(f1, f2, f3)     : return (f1, f2, f3)
def vec4(f1, f2, f3, f4) : return (f1, f2, f3, f4)

class ShaderException(Exception):
    def __init__(self, type, msg):
        self.type = type # "compile" or "link"
        self.msg = msg
    def __str__(self):
        return "Error during %s:\n%s" % (self.type, self.msg)
       
class FragmentShader(object):
   
    def __init__(self, source):
        self._source   = source # GLSL fragment shader code.
        self._shader   = self._compile_shader()
        self._program  = self._create_program(self._shader)
        self._active   = False
        self.variables = {}
    
    def _compile_shader(self):
        """ Compiles the GLSL source code, checking for errors along the way.
        """
        shader = glCreateShader(GL_FRAGMENT_SHADER)
        length = c_int(-1)
        glShaderSource(shader, 1, cast(byref(c_char_p(self._source)), POINTER(POINTER(c_char))), byref(length))
        glCompileShader(shader)
        status = c_int(-1)
        glGetShaderiv(shader, GL_COMPILE_STATUS, byref(status))
        if status.value == 0:
            glDeleteShader(shader)
            raise ShaderException("compile", self._shader_info_log(shader))
        else:
            return shader
       
    def _create_program(self, shader):
        """ Creates an OpenGL program from the compiled shader.
        """
        program = glCreateProgram()
        glAttachShader(program, shader)
        glLinkProgram(program)
        status = c_int(-1)
        glGetProgramiv(program, GL_LINK_STATUS, byref(status ))
        if status .value == 0:
            glDeleteProgram(program)
            raise ShaderException("link", self._program_info_log(program))
        else:
            return program
    
    def _shader_info_log(self, shader):
        length = c_int()
        glGetShaderiv(shader, GL_INFO_LOG_LENGTH, byref(length))       
        if length.value > 0:
            log = create_string_buffer(length.value)
            glGetShaderInfoLog(shader, length, byref(length), log)
            return log.value
        return ""

    def _program_info_log(self, program):
        length = c_int()
        glGetProgramiv(program, GL_INFO_LOG_LENGTH, byref(length))
        if length.value > 0:
            log = create_string_buffer(length.value)
            glGetProgramInfoLog(program, length, byref(length), log)
            return log.value
        return ""

    def get(self, name):
        return self.variables[name]
    
    def set(self, name, value):
        """ Provides an easy way to set uniform variables in the GLSL source script.
            This will work for vec2, vec3, vec4, list of int or float, single int or float.
            We wait until glUseProgram() to pass them to the source.
        """
        self.variables[name] = value
        if self._active:
            self._set(name, value)
    
    def _set(self, name, value):
        address = glGetUniformLocation(self._program, name)
        # A tuple with 2, 3 or 4 floats representing vec2, vec3 or vec4.
        if isinstance(value, tuple):
            if len(value) == 2:
                glUniform2f(address, value[0], value[1])
            elif len(value) == 3:
                glUniform3f(address, value[0], value[1], value[2])
            elif len(value) == 4:
                glUniform4f(address, value[0], value[1], value[2], value[3])
        # A list representing an array of ints or floats.
        elif isinstance(value, list):
            if find(lambda v: isinstance(v, float), value):
                array = c_float * len(value)
                glUniform2fv(address, len(value), array(*value))
            else:
                array = c_int * len(value)
                glUniform2iv(address, len(value), array(*value))
        # Single float value.
        elif isinstance(value, float):
            glUniform1f(address, value)
        # Single int value or named texture.
        elif isinstance(value, int):
            glUniform1i(address, value)
    
    def push(self):
        """ Installs the program and sets its variables.
        """
        self._active = True
        glUseProgram(self._program)
        for k, v in self.variables.items():
            self._set(k, v)
            
    def pop(self):
        # Note that shaders can't be nested since pop() just removes any active shader.
        if self._active == True:
            glUseProgram(0)
            self._active = False
    
    @property
    def active(self):
        return self._active
    
    def __del__(self):
        try:
            glDetachShader(self._program, self._shader)
            glDeleteProgram(self._program) # XXX - throws a segmentation error. Leak?
            glDeleteShader(self._shader)
        except:
            pass

#=====================================================================================================

#--- FILTER ------------------------------------------------------------------------------------------
# Stores a shader's variables and applies them once push() is called.
# This way we can pass many filters of the same type, but with different arguments, to a render chain.

class Filter(object):
    def __init__(self):
        # Shader and its variables need to be stored here.
        self._shader = None
        self.image = None
    def push(self):
        # Shader needs to set its variables here.
        #self._shader.set(variable, value)
        self._shader.push()
    def pop(self):
        self._shader.pop()

#--- BLUR --------------------------------------------------------------------------------------------
# Gaussian blur with a 3x3, 5x5, 7x7, 9x9 or 11x11 convolution kernel.

_blur = {}
_blur[3] = FragmentShader('''
uniform sampler2D src;
uniform vec2 offset;
void main() {
	vec2 base = gl_TexCoord[0].st;
	gl_FragColor = 
	  0.52201146875401894 *  texture2D(src, base)
	+ 0.23899426562299048 * (texture2D(src, base - offset) + texture2D(src, base + offset));
}''')

_blur[5] = FragmentShader('''
uniform sampler2D src;
uniform vec2 offset;
void main() {
	vec2 base = gl_TexCoord[0].st;
	gl_FragColor = 
	  0.28083404410305668 *  texture2D(src, base)
	+ 0.23100778343685141 * (texture2D(src, base -     offset) + texture2D(src, base +     offset))
	+ 0.12857519451162022 * (texture2D(src, base - 2.0*offset) + texture2D(src, base + 2.0*offset));
}''')

_blur[7] = FragmentShader('''
uniform sampler2D src;
uniform vec2 offset;
void main() {
	vec2 base = gl_TexCoord[0].st;
	gl_FragColor = 
	  0.17524014277641392 *  texture2D(src, base)
	+ 0.16577007239192226 * (texture2D(src, base -     offset) + texture2D(src, base +     offset))
	+ 0.14032133681355632 * (texture2D(src, base - 2.0*offset) + texture2D(src, base + 2.0*offset))
	+ 0.10628851940631442 * (texture2D(src, base - 3.0*offset) + texture2D(src, base + 3.0*offset));
}''')

_blur[9] = FragmentShader('''
uniform sampler2D src;
uniform vec2 offset;
void main() {
	vec2 base = gl_TexCoord[0].st;
	gl_FragColor = 
      0.13465835724954514  *  texture2D(src, base)
    + 0.13051535514624768  * (texture2D(src, base -     offset) + texture2D(src, base +     offset))
    + 0.11883558317985349  * (texture2D(src, base - 2.0*offset) + texture2D(src, base + 2.0*offset))
    + 0.1016454607907402   * (texture2D(src, base - 3.0*offset) + texture2D(src, base + 3.0*offset))
    + 0.081674422258386087 * (texture2D(src, base - 4.0*offset) + texture2D(src, base + 4.0*offset));
}''')

_blur[11] = FragmentShader('''
uniform sampler2D src;
uniform vec2 offset;
void main() {
	vec2 base = gl_TexCoord[0].st;
	gl_FragColor = 
      0.1093789154396443   *  texture2D(src, base)
    + 0.1072130678016711   * (texture2D(src, base -     offset) + texture2D(src, base +     offset))
    + 0.10096946479237721  * (texture2D(src, base - 2.0*offset) + texture2D(src, base + 2.0*offset))
    + 0.091360949823207332 * (texture2D(src, base - 3.0*offset) + texture2D(src, base + 3.0*offset))
    + 0.079425394122662363 * (texture2D(src, base - 4.0*offset) + texture2D(src, base + 4.0*offset))
    + 0.066341665740259792 * (texture2D(src, base - 5.0*offset) + texture2D(src, base + 5.0*offset));
}''')

class Blur(Filter):
    def __init__(self, image, scale=1.0, kernel=5):
        self._shader = _blur[kernel]
        self.image = image
        self.scale = scale    
    def push(self):
        self._shader.set("offset", vec2(self.scale/self.image.width, self.scale/self.image.height))
        self._shader.push()

#--- COLORIZE ---------------------------------------------------------------------------------------
# Multiplies source color values and adds a bias factor to each color component.

_colorize = FragmentShader('''
uniform sampler2D src;
uniform vec4 color;
uniform vec4 bias;
void main() {
  vec4 base = texture2D(src, gl_TexCoord[0].st);
  gl_FragColor = clamp(base * color + bias, 0.0, 1.0);
}''')

class Colorize(Filter):
    def __init__(self, image, color=vec4(1,1,1,1), bias=vec4(0,0,0,0)):
        self._shader = _colorize
        self.image = image
        self.color = color
        self.bias  = bias
    def push(self):
        self._shader.set("color", self.color)
        self._shader.set("bias",  self.bias)
        self._shader.push()

#--- BLEND MODES -------------------------------------------------------------------------------------

_blend = {}
_blend["multiply"] = FragmentShader('''
uniform sampler2D src1;
uniform sampler2D src2;
uniform float opacity;
void main() {
    vec4 base  = texture2D(src1, gl_TexCoord[0].st);
    vec4 blend = texture2D(src2, gl_TexCoord[0].st);
    vec4 result = clamp(blend * base, 0.0, 1.0);
    gl_FragColor = mix(base, result, opacity);
}''')

class Blend(Filter):
    def __init__(self, mode, image, blend, opacity=1.0):
        self._shader = _blend[mode]
        self.image = image
        self.blend = blend # the image to blend on top of the base
        self.opacity = opacity
    def push(self):
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(self.image.target, self.image.id)        
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(self.blend.target, self.blend.id)
        glActiveTexture(GL_TEXTURE0)
        self._shader.set("src1", 0)
        self._shader.set("src2", 1)
        self._shader.set("opacity", self.opacity)
        self._shader.push()

#--- GRADIENTS ---------------------------------------------------------------------------------------

_gradient = {}
_gradient["linear"] = FragmentShader('''
uniform sampler2D src;
uniform vec4 clr1;
uniform vec4 clr2;
uniform vec2 size;
void main() {
    float t = gl_TexCoord[0].t;
    gl_FragColor = clr1*t + clr2*(1.0-t);
}''')

_gradient["radial"] = FragmentShader('''
uniform sampler2D src;
uniform vec4 clr1;
uniform vec4 clr2;
uniform vec2 size;
void main() {
    float dx = gl_TexCoord[0].x - 0.5;
    float dy = gl_TexCoord[0].y - 0.5;
    float d = 4.0 * (dx*dx+dy*dy);
    gl_FragColor = clr1*d + clr2*(1.0-d);
}''')

class LinearGradient(Filter):
    def __init__(self, image, clr1=vec4(0,0,0,0), clr2=vec4(1,1,1,1)):
        self._shader = _gradient["linear"]
        self.image  = image
        self.clr1 = clr1
        self.clr2 = clr2
    def push(self):
        self._shader.set("size", vec2(ceil2(self.image.width), ceil2(self.image.height)))
        self._shader.set("clr1", self.clr1)
        self._shader.set("clr2", self.clr2)
        self._shader.push()

class RadialGradient(Filter):
    def __init__(self, image, clr1=vec4(0,0,0,1), clr2=vec4(1,1,1,1)):
        self._shader = _gradient["radial"]
        self.image  = image
        self.clr1 = clr1
        self.clr2 = clr2
    def push(self):
        self._shader.set("size", vec2(ceil2(self.image.width), ceil2(self.image.height)))
        self._shader.set("clr1", self.clr1)
        self._shader.set("clr2", self.clr2)
        self._shader.push()

#=====================================================================================================

#--- FRAME BUFFER OBJECT -----------------------------------------------------------------------------
# "FBO" is an OpenGL extension to do "Render to Texture", offscreen drawing in a buffer.
# http://www.gamedev.net/reference/articles/article2331.asp
# We can also use this to chain multiply fragment shaders.

class FBO:
    
    def __init__(self, width, height):
        self.id = c_uint(0)
        glGenFramebuffersEXT(1, byref(self.id))
        self.width  = width
        self.height = height
        #self._depthbuffer = self._init_depthbuffer(width, height)
        self._texture = self._init_texture(width, height)
        self.draw = FBO_draw
    
    def _init_depthbuffer(self, width, height):
        # A depth buffer is used in 3D to decide which elements hide the ones behind.
        id = c_uint(0)
        glGenRenderbuffersEXT(1, byref(id))
        glBindRenderbufferEXT(GL_RENDERBUFFER_EXT, id)
        glRenderbufferStorageEXT(GL_RENDERBUFFER_EXT, GL_DEPTH_COMPONENT, width, height)
        glFramebufferRenderbufferEXT(
            GL_FRAMEBUFFER_EXT,
            GL_DEPTH_ATTACHMENT_EXT,
            GL_RENDERBUFFER_EXT,
            id
        )
        return id
    
    def _init_texture(self, width, height):
        #img = c_uint(0)
        #glGenTextures(1, byref(img))
        #glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
        img = pyglet.image.Texture.create(width, height)
        return img

    @property
    def texture(self):
        return self._texture

    image = texture
    
    def slice(self, x, y, width, height):
        return self._texture.get_region(x, y, width, height)

    @property
    def active(self):
        # Check after glBindFramebufferEXT() and glFramebufferTexture2DEXT(), i.e. after push().
        return glCheckFramebufferStatusEXT(GL_FRAMEBUFFER_EXT) == GL_FRAMEBUFFER_COMPLETE_EXT
    
    def refresh(self):
        # Update depth buffer and texture when width or height changes.
        if self._texture.width != self.width \
        or self._texture.height != self.height:
            #glDeleteRenderbuffersEXT(1, self._depthbuffer)
            #self._depthbuffer = self._init_depthbuffer(self.width, self.height)
            self._texture = self._init_texture(self.width, self.height)        
    
    def push(self):
        """ Between push() and pop(), all drawing is done offscreen on FBO.texture.
        """
        self.refresh()
        # XXX - don't we need to clear the previous buffer, like:
        #self._texture = self._init_texture(self.width, self.height)
        glBindTexture(self._texture.target, self._texture.id)
        #glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        #glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, self.id.value)
        glFramebufferTexture2DEXT(
            GL_FRAMEBUFFER_EXT, 
            GL_COLOR_ATTACHMENT0_EXT, 
            self._texture.target, 
            self._texture.id, 
            self._texture.level
        )
        #glPushAttrib(GL_VIEWPORT_BIT)
        #glViewport(0, 0, self.width, self.height)
    
    def pop(self):
        #glPopAttrib()
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, 0)
    
    def render(self):
        """ Executes offscreen drawing commands in self.draw() patch and returns texture.
        """
        self.push()
        self.draw(self)
        self.pop()
        return self.texture
    
    def __del__(self):
        try:
            glDeleteFramebuffersEXT(1, self.id)
            #glDeleteRenderbuffersEXT(1, self._depthbuffer)
        except:
            pass

def FBO_draw(FBO):
    pass
