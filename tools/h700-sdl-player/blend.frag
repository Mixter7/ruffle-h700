#version 300 es
precision highp float;
uniform sampler2D source_image;
uniform sampler2D backdrop_image;
uniform vec2 image_size;
uniform int blend_mode;
out vec4 result;
void main() {
    vec2 uv=gl_FragCoord.xy/image_size;
    vec4 s=texture(source_image,uv), d=texture(backdrop_image,uv);
    vec3 cs=s.a>0.0 ? s.rgb/s.a : vec3(0.0);
    vec3 cd=d.a>0.0 ? d.rgb/d.a : vec3(0.0);
    vec3 b=cs;
    if (blend_mode==3) b=cs*cd;
    else if (blend_mode==6) b=min(cs,cd);
    else if (blend_mode==14) b=mix(2.0*cs*cd,1.0-2.0*(1.0-cs)*(1.0-cd),step(vec3(0.5),cs));
    result=vec4((1.0-s.a)*d.rgb+(1.0-d.a)*s.rgb+s.a*d.a*b,s.a+d.a-s.a*d.a);
}
