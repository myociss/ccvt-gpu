var jumpFloodShader = 
    `uniform int stepSize;

    bool between(const vec2 value, const vec2 bottom, const vec2 top) {
        return (
            all(greaterThan(value, bottom)) &&
            all(lessThan(value, top))
        );
    }

    bool validUv(const vec2 uv) {
        return between(
                uv,
                vec2(0., 0.),
                vec2(1., 1.)
            );
        }

    vec3 compareNeighbor(const vec2 myUv, const vec2 myLabel, const float mySeedId, const vec2 offset){
        //what is the other uv?
        vec2 otherUv = (gl_FragCoord.xy + offset) / resolution.xy;

        //is that a valid uv?
        if(!validUv(otherUv)){
            return vec3(myLabel, mySeedId);
        }

        //what color does it have?
        vec4 otherColor = texture2D(jumpFlood, otherUv);

        //what label does that translate to?
        vec2 otherLabel = vec2(otherColor[0], otherColor[1]);

        //what seed id is that?
        float otherSeedId = otherColor[2];

        //i am invalid
        if(all(equal(myLabel,vec2(1.0, 1.0)))){
            //we are both invalid
            if(all(equal(otherLabel,vec2(1.0,1.0)))){
                return vec3(1.0, 1.0, 1.0);
            }
            //only i am invalid
            return vec3(otherLabel, otherSeedId);
        }

        //other is invalid but i am valid
        if(all(equal(otherLabel, vec2(1.0,1.0)))){
            return vec3(myLabel, mySeedId);
        }

        //both of us are valid
        float myDist = distance(myUv, myLabel);
        float otherDist = distance(myUv, otherLabel);
                
        float minDist = min(myDist, otherDist);

        if(minDist==myDist){
            return vec3(myLabel, mySeedId);;
        }

        return vec3(otherLabel, otherSeedId);
    }

    void main() {
        //where am i?
        vec2 uv = gl_FragCoord.xy / resolution.xy;

        //what color do i have?
        vec4 myColor = texture2D(jumpFlood, uv);

        //what label does that translate to?
        vec2 myLabel = vec2(myColor[0], myColor[1]);

        //what is my seed id if any?
        float mySeedId = myColor[2];

        //how far from my label am i?
        float myDist = distance(uv, myLabel);

        int myStepSize = stepSize;

        //how close to my label am i compared to the labels my neighbors have?
        vec3 myNewLabel = compareNeighbor(uv, myLabel, mySeedId, vec2(0, myStepSize));
                
        vec2 myNewPos = vec2(myNewLabel[0], myNewLabel[1]);
        float myNewSeedId = myNewLabel[2];

        myNewLabel = compareNeighbor(uv, myNewPos, myNewSeedId, vec2(myStepSize, myStepSize));
        myNewPos = vec2(myNewLabel[0], myNewLabel[1]);
        myNewSeedId = myNewLabel[2];


        myNewLabel = compareNeighbor(uv, myNewPos, myNewSeedId, vec2(myStepSize, 0));
        myNewPos = vec2(myNewLabel[0], myNewLabel[1]);
        myNewSeedId = myNewLabel[2];

        myNewLabel = compareNeighbor(uv, myNewPos, myNewSeedId, vec2(myStepSize, - myStepSize));
        myNewPos = vec2(myNewLabel[0], myNewLabel[1]);
        myNewSeedId = myNewLabel[2];

        myNewLabel = compareNeighbor(uv, myNewPos, myNewSeedId, vec2(0, - myStepSize));
        myNewPos = vec2(myNewLabel[0], myNewLabel[1]);
        myNewSeedId = myNewLabel[2];

        myNewLabel = compareNeighbor(uv, myNewPos, myNewSeedId, vec2(- myStepSize, - myStepSize));
        myNewPos = vec2(myNewLabel[0], myNewLabel[1]);
        myNewSeedId = myNewLabel[2];

        myNewLabel = compareNeighbor(uv, myNewPos, myNewSeedId, vec2(- myStepSize, 0));
        myNewPos = vec2(myNewLabel[0], myNewLabel[1]);
        myNewSeedId = myNewLabel[2];

        myNewLabel = compareNeighbor(uv, myNewPos, myNewSeedId, vec2(- myStepSize, myStepSize));

        gl_FragColor = vec4(myNewLabel, 1.0);
    }`;

var reduceVerticesShader = 
    `
    uniform sampler2D pixelPosition;
    uniform float res;
    attribute vec2 reference;
    varying lowp vec4 vColor;
    varying vec2 vUv;

    void main() {
        vUv = reference;
        gl_PointSize = 1.0;

        vec4 textureColor = texture2D( pixelPosition, reference );
        float seedId = textureColor[2];

        //vColor = vec4(textureColor[0], textureColor[1], 1.0, 1.0);
        vColor = vec4(reference, 1.0, 1.0);
        gl_Position = vec4((seedId * 2.0) + -1.0 + (1.0/res),
            -1.0 + (1.0/res), 0, 1.0);        
    }`;

var reduceVerticesFragShader =
    `
    //uniform sampler2D pixelPosition;
    //varying vec2 vUv;
    varying lowp vec4 vColor;

    void main() {
        //gl_FragColor = texture2D(pixelPosition, vUv);
        gl_FragColor = vColor;
    }`;

var centroidPlacementShaderMain = 
    `
    uniform sampler2D centroidPlacement;
    uniform float numSeeds;
    uniform vec2 errorBound;
    uniform float res;

    bool between(const vec2 value, const vec2 bottom, const vec2 top) {
        return (
            all(greaterThan(value, bottom)) &&
            all(lessThan(value, top))
        );
    }

    void main(){
        vec2 uv = gl_FragCoord.xy / resolution.xy;
        gl_FragColor = vec4(1.0, 1.0, 1.0, 1.0);
        vec2 seed;
        vec2 centroidLabel;
        vec2 centroidPos;
        vec4 centroidColorStored;
        vec4 centroidColor;
    `;