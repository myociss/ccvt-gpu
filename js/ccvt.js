function ccvt(res, numSeeds){
    var gpuComputeVoronoi = new GPUComputationRenderer( res, res, renderer );
    var voronoiTexture = initVoronoiTexture(numSeeds, res);
    var jfVar = gpuComputeVoronoi.addVariable( 'jumpFlood', jumpFloodShader, voronoiTexture );
    var jfUniforms = jfVar.material.uniforms;

    jfUniforms['stepSize'] = {value: 0};
    gpuComputeVoronoi.setVariableDependencies( jfVar, [ jfVar ] );
    gpuComputeVoronoi.init();
    jfaPlusOne(jfVar, gpuComputeVoronoi, res);

    var newSeedMesh = initNewSeedCalcMesh(numSeeds, res);
    var newSeedRt = gpuComputeVoronoi.createRenderTarget(res, res, null, null, THREE.NearestFilter, 
        THREE.NearestFilter);
    newSeedMesh.material.uniforms['pixelPosition'].value = 
        gpuComputeVoronoi.getCurrentRenderTarget(jfVar).texture;
    getNewCentroidTexture(newSeedMesh, newSeedRt, res);
    return newSeedRt.texture;
    
    
    //return newSeedRt.texture;
    
    //var centroidTextureMesh = initCentroidTextureMesh(numSeeds, res);
    //var centroidRenderTarget = gpuComputeVoronoi.createRenderTarget(res, res, null, null, THREE.NearestFilter, 
    //    THREE.NearestFilter);
    //renderCentroidsToTexture(centroidTextureMesh, centroidRenderTarget, numSeeds, res);
    //return centroidRenderTarget.texture;

    //return jfaPlusOne(jfVar, gpuComputeVoronoi, res);
}

function writeCentroidPlacementShader(numSeeds){
    var centroidPlacementShader = centroidPlacementShaderMain;
    for (var i=0; i < numSeeds; i++){
        centroidPlacementShader += 
        `
        seed = vec2(${i}, 0) / resolution.xy;
        centroidColor = texture2D(centroidPlacement, seed );
        centroidPos = vec2(centroidColor[0], centroidColor[1]);

        if(between(uv, vec2(centroidPos - errorBound), vec2(centroidPos + errorBound))){
            gl_FragColor = vec4(1.0, 0.0, 0.0, 1.0);
        }
        `;
    }
    centroidPlacementShader += `}`;
    //console.log(centroidPlacementShader);
    return centroidPlacementShader
}

function initNewSeedCalcMesh(numSeeds, res){
    var pointGeometry = new THREE.BufferGeometry();
    var positions = [];

    for(var i=0; i < res; i++){
        for(var j=0; j < res; j++){
            positions.push(i, j, 0);
        }
    }

    pointGeometry.addAttribute( 'position', new THREE.Float32BufferAttribute( positions, 3 ) );
    var referenceArray = [];
            
    for(var i=0; i < res; i++){
        for(var j=0; j < res; j++){
            referenceArray.push(i / res, j / res);
        }
    }

    pointGeometry.addAttribute( 'reference', new THREE.Float32BufferAttribute( referenceArray, 2 )  );
    
    var pointUniforms = {
        pixelPosition: { type: "t", value: null },
        res: { value: res }
        
    };

    var pointMaterial = new THREE.ShaderMaterial({
        uniforms: pointUniforms,
        vertexShader: reduceVerticesShader,
        fragmentShader: reduceVerticesFragShader
    });

    var pointMesh = new THREE.Points(pointGeometry, pointMaterial);
    return pointMesh;
}


function initCentroidTextureMesh(numSeeds, res){
    var centroidTextureUniforms = {
        centroidPlacement: { type: "t", value: null },
        numSeeds: {value: numSeeds},
        errorBound: {value: [0.9 / res, 0.9 / res]}
        
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

function getNewCentroidTexture(pointMesh, pointRenderTarget, res){
    var rtScene = new THREE.Scene;
    rtScene.background = new THREE.Color( 0xffffff );
    //pointMesh.material.uniforms['pixelPosition'] = 
    rtScene.add(pointMesh);
    var width = res;
    var height = res;
    //var rtCamera = new THREE.OrthographicCamera(width/- 2, width/2, height/2, height/- 2, 0.1);
    var rtCamera = new THREE.Camera();
    rtCamera.position.z = 1;
    //var currentWindow = renderer.getDrawingBufferSize();
    var currentRenderTarget = renderer.getRenderTarget();

    var currentSize = new THREE.Vector2();
    renderer.getDrawingBufferSize(currentSize);
    
    //renderer.setSize(res, res);
    renderer.setRenderTarget(pointRenderTarget);
    renderer.render(rtScene, rtCamera);

    //not sure if changing the size back is actually necessary....
    //renderer.setSize(currentSize.x, currentSize.y);
    //currentRenderTarget.add(pointMesh);
    renderer.setRenderTarget(currentRenderTarget);
    //renderer.render(rtScene, rtCamera);
}


function renderCentroidsToTexture(centroidMesh, centroidRenderTarget, numSeeds, res){
    var rtScene = new THREE.Scene();
    //rtScene.background = new THREE.Color( 0xffffff );
    centroidMesh.material.uniforms['centroidPlacement'].value = myCreateTexture(res, res);
    console.log(centroidMesh.material.uniforms['centroidPlacement'].value);
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
    //texture[1] = [90/128, 50/128, 1.0, 1.0];
    //texture.image.data[0] = 25 / 128;
    //texture.image.data[1] = 40 / 128;
    for(var i=0; i < 14; i++){
        var idx = i * 4;
        texture.image.data[idx] = getRandomInt(0, 127) / 128;
        texture.image.data[idx + 1] = getRandomInt(0, 127) / 128;
    }

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
        var seedId = i / res;
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