function ccvt(res, numSeeds){
    var gpuComputeVoronoi = new GPUComputationRenderer( res, res, renderer );
    var voronoiTexture = initVoronoiTexture(numSeeds, res);
    var jfVar = gpuComputeVoronoi.addVariable( 'jumpFlood', jumpFloodShader, voronoiTexture );
    var jfUniforms = jfVar.material.uniforms;

    jfUniforms['stepSize'] = {value: 0};
    gpuComputeVoronoi.setVariableDependencies( jfVar, [ jfVar ] );
    gpuComputeVoronoi.init();

    /*var gpuComputeNewSeeds = new GPUComputationRenderer(numSeeds, 0, renderer);
    var computeSeedsTexture = gpuComputeNewSeeds.createTexture();
    var computeSeedsVar = gpuComputeNewSeeds.addVariable('centroidPlacement', writeCentroidPlacementShader(numSeeds), computeSeedsTexture);
    computeSeedsTexture.setVariableDependencies(computeSeedsVar, [ computeSeedsVar] );
    gpuComputeNewSeeds.init();*/
    var centroidTextureMesh = initCentroidTextureMesh(numSeeds, res);
    var centroidRenderTarget = gpuComputeVoronoi.createRenderTarget(res, res, null, null, THREE.NearestFilter, 
        THREE.NearestFilter);
    renderCentroidsToTexture(centroidTextureMesh, centroidRenderTarget, numSeeds);
    return centroidRenderTarget.texture;

    //return jfaPlusOne(jfVar, gpuComputeVoronoi, res);
}

function writeCentroidPlacementShader(numSeeds){
    var centroidPlacementShader = 
    `
        uniform sampler2D centroidPlacement;
        uniform float numSeeds;

        bool between(const vec2 value, const vec2 bottom, const vec2 top) {
            return (
                all(greaterThan(value, bottom)) &&
                all(lessThan(value, top))
            );
        }

        void main(){
            vec2 uv = gl_FragCoord.xy / resolution.xy;
            gl_FragColor = vec4(1.0, 1.0, 1.0, 1.0);
    `;
    for (var i=numSeeds - 1; i >= 1; i--){
        centroidPlacementShader += 
        `
        vec2 seed${i} = vec2(${i}, 0) / vec2(numSeeds, 1);
        vec4 centroidPos${i} = texture2D(centroidPlacement, seed${i} );
        float centroidPosX${i} = centroidPos${i}[0];
        float centroidPosY${i} = centroidPos${i}[1];

        gl_FragColor = vec4(centroidPosX${i} / resolution.x, centroidPosY${i} / resolution.y, 1.0, 1.0);

        if(between(gl_FragCoord.xy, vec2(centroidPosX${i} - 1, -1), vec2(centroidPosY${i} + 1, 1))){
            gl_FragColor = vec4(1.0, 1.0, 1.0, 1.0);
        }

        //gl_FragColor = vec4(gl_FragCoord.x, 0.0, 1.0, 1.0);
        
        //gl_FragColor = vec4(uv[0], uv[1], 1.0, 1.0);
        //if(all(equal(vec2(uv[0], 0.0), vec2(0.0, 0.0)))){
        //    gl_FragColor = vec4(1.0, 0.0, 0.0, 1.0);
        //}
        `;
    }
    centroidPlacementShader += `}`
    return centroidPlacementShader
}

function initCentroidTextureMesh(numSeeds, res){
    var centroidTextureUniforms = {
        centroidPlacement: { type: "t", value: null },
        numSeeds: {value: numSeeds}
        
    };

    var vertexPassShader = 
    `
        void main()	{
            gl_Position = vec4( position, 1.0 );
		}
    `

    var centroidMaterial = new THREE.ShaderMaterial({
        uniforms: centroidTextureUniforms,
        vertexShader: vertexPassShader,
        fragmentShader: writeCentroidPlacementShader(numSeeds)
    });
    centroidMaterial.defines.resolution = 'vec2( ' + res.toFixed( 1 ) + ', ' + res.toFixed( 1 ) + ' )';

    var centroidMesh = new THREE.Mesh( new THREE.PlaneBufferGeometry( 2, 2 ), centroidMaterial );
    return centroidMesh;
}

function renderCentroidsToTexture(centroidMesh, centroidRenderTarget, numSeeds){
    var rtScene = new THREE.Scene();
    centroidMesh.material.uniforms['centroidPlacement'] = myCreateTexture(numSeeds, 1)
    rtScene.add(centroidMesh);

	var rtCamera = new THREE.Camera();
    rtCamera.position.z = 1;
    
    var currentRenderTarget = renderer.getRenderTarget();

    renderer.setRenderTarget(centroidRenderTarget);
    renderer.render(rtScene, rtCamera);

    renderer.setRenderTarget( currentRenderTarget );
}

function myCreateTexture(sizeX, sizeY) {

    var a = new Float32Array( sizeX * sizeY * 4 );
    var texture = new THREE.DataTexture( a, sizeX, sizeY, THREE.RGBAFormat, THREE.FloatType );
    texture.needsUpdate = true;

    //texture[0] = [100, 50, 1.0, 1.0];
    //texture[1] = [90, 50, 1.0, 1.0];

    return texture;

};

/*function initCentroidTextureRenderer(res, centroidTextureMesh){
    var rtScene = new THREE.Scene();

	var rtCamera = new THREE.Camera();
    rtCamera.position.z = 1;
    
    var renderTarget = gpuCompute.createRenderTarget(res, res, null, null, THREE.NearestFilter, 
        THREE.NearestFilter);
    //textureRenderer.setRenderTarget(renderTarget);
    
}*/

function jfaPlusOne(jfVar, gpuCompute, res){
    var jfUniforms = jfVar.material.uniforms;

    jfUniforms['stepSize'].value = 1;
    gpuCompute.compute();

    var stepSize = 2 ** (Math.ceil(Math.log2(res)) - 1);
    while(stepSize >= 1.0){
        console.log(stepSize)
        jfUniforms['stepSize'].value = stepSize;
        gpuCompute.compute();
        stepSize /= 2;
    }

    return gpuCompute.getCurrentRenderTarget(jfVar).texture;
}


function reduceRegions(numSeeds){
    var width = 2 * numSeeds;
    var height = 2;
    var rtCamera = new THREE.OrthographicCamera( width / - 2, width / 2, height / 2, height / - 2, 1, 1000 );
    
    var rtScene = new THREE.Scene();
    rtScene.background = new THREE.Color( 0xff0000 );
    rtScene.add(camera);
    var textureRenderer = new THREE.WebGLRenderer();
    textureRenderer.setSize( width, height );
    var renderTarget = gpuCompute.createRenderTarget(width, height, null, null, THREE.NearestFilter, 
        THREE.NearestFilter);
    textureRenderer.setRenderTarget(renderTarget);
    textureRenderer.render(rtScene, rtCamera);
    textureRenderer.setRenderTarget(null);
}

function initSeedsTexture(numSeeds, width, height, renderer){
    data = [];
    for(var i=0; i < numSeeds; i++){
        data.push([0.0, 0.0, 0.0, 1.0]);
    }
    var seedsTexture = new THREE.DataTexture( data, res, res, THREE.RGBAFormat, THREE.FloatType );
    seedsTexture.needsUpdate = true;
    seedsCompute = new GPUComputationRenderer( width, height, renderer );
}




function initVoronoiTexture(numSeeds, res){
    var seeds = getStartingSeeds(numSeeds, res, res);

    var seedData = [];

    for(var i=0; i < res; i++){
        seedData.push([]);
        for(var j=0; j < res; j++){
            seedData[i].push([1.0,1.0,1.0,1.0]);
        }
    }

    for(var i=0; i < seeds.length; i++){
        var x = seeds[i][0] / res;
        var y = seeds[i][1] / res;
        var seedId = i / seeds.length;
        seedData[seeds[i][0]][seeds[i][1]] = [x, y, seedId, 1.0];
    }

    var data = new Float32Array( 4 * (res * res) );

    for(var i=0; i < res; i++){
        for(var j=0; j < res; j++){
            var dataIdx = 4 * ((i * res) + j);
            data[dataIdx] = seedData[i][j][0];
            data[dataIdx + 1] = seedData[i][j][1];
            data[dataIdx + 2] = seedData[i][j][2];
            data[dataIdx + 3] = seedData[i][j][3];
        }
    }

    var voronoiTexture = new THREE.DataTexture( data, res, res, THREE.RGBAFormat, THREE.FloatType );
    voronoiTexture.needsUpdate = true;
    return voronoiTexture;
}


function getStartingSeeds(numSeeds, width, height){
    var seeds = [];
    for(var i=0; i < numSeeds; i++){
        seeds.push(getSeed(seeds, width, height));
    }
    return seeds;
}


function getSeed(seedsArray, width, height){
    var randomSeed = [getRandomInt(0, width-1), getRandomInt(0, height-1)];
    while(seedInvalid(seedsArray, randomSeed)){
        randomSeed = [getRandomInt(0, width-1), getRandomInt(0, height-1)];
    }
    return randomSeed;
}

function seedInvalid(seedsArray, seed){
    var invalid = false;
    for(var i=0; i < seedsArray.length; i++){
        var seed0 = seedsArray[i];
        if(dist(seed0, seed) < 5){
            invalid = true;
            break;
        }
    }
    return invalid;
}

function getRandomInt(min, max) {
    min = Math.ceil(min);
    max = Math.floor(max);
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

function dist(a, b){
    var xDist = (a[0] - b[0])**2;
    var yDist = (a[1] - b[1])**2;
    return Math.sqrt(xDist + yDist);
}