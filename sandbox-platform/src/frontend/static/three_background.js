/**
 * Threat Constellation — Three.js Background
 * Cybersecurity node network rendered behind UI
 */
(function () {
    'use strict';

    // Adaptive quality detection
    const cores = navigator.hardwareConcurrency || 2;
    const mem = navigator.deviceMemory || 4;
    const isMobile = /Mobi|Android/i.test(navigator.userAgent);
    const quality = (cores >= 8 && mem >= 8 && !isMobile) ? 'high'
                  : (cores >= 4 && mem >= 4) ? 'medium' : 'low';

    if (quality === 'low' || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    const CONFIG = {
        high:   { nodes: 120, edges: 180, particleCount: 300, bloomStrength: 0.4 },
        medium: { nodes: 60,  edges: 90,  particleCount: 100, bloomStrength: 0.2 },
    }[quality];

    const canvas = document.createElement('canvas');
    canvas.id = 'three-bg-canvas';
    document.body.prepend(canvas);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.z = 50;

    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: quality === 'high' });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, quality === 'high' ? 2 : 1));
    renderer.setClearColor(0x000000, 0);

    // Node data
    const nodePositions = [];
    const nodeVelocities = [];
    const SPREAD = 60;

    for (let i = 0; i < CONFIG.nodes; i++) {
        nodePositions.push(
            (Math.random() - 0.5) * SPREAD * 2,
            (Math.random() - 0.5) * SPREAD,
            (Math.random() - 0.5) * 30 - 15
        );
        nodeVelocities.push(
            (Math.random() - 0.5) * 0.02,
            (Math.random() - 0.5) * 0.02,
            (Math.random() - 0.5) * 0.01
        );
    }

    // Instanced spheres for nodes
    const nodeGeo = new THREE.SphereGeometry(0.15, 8, 6);
    const nodeMat = new THREE.MeshBasicMaterial({ color: 0x6366f1, transparent: true, opacity: 0.6 });
    const nodesMesh = new THREE.InstancedMesh(nodeGeo, nodeMat, CONFIG.nodes);
    scene.add(nodesMesh);

    const dummy = new THREE.Object3D();
    function updateNodeInstances() {
        for (let i = 0; i < CONFIG.nodes; i++) {
            dummy.position.set(nodePositions[i * 3], nodePositions[i * 3 + 1], nodePositions[i * 3 + 2]);
            dummy.updateMatrix();
            nodesMesh.setMatrixAt(i, dummy.matrix);
        }
        nodesMesh.instanceMatrix.needsUpdate = true;
    }
    updateNodeInstances();

    // Glow points
    const glowGeo = new THREE.BufferGeometry();
    const glowPositions = new Float32Array(CONFIG.nodes * 3);
    for (let i = 0; i < CONFIG.nodes * 3; i++) glowPositions[i] = nodePositions[i];
    glowGeo.setAttribute('position', new THREE.BufferAttribute(glowPositions, 3));
    const glowMat = new THREE.PointsMaterial({
        color: 0x6366f1, size: 1.2, transparent: true, opacity: 0.25,
        blending: THREE.AdditiveBlending, depthWrite: false
    });
    const glowPoints = new THREE.Points(glowGeo, glowMat);
    scene.add(glowPoints);

    // Edges — connect nearby nodes
    function buildEdges() {
        const edgeVerts = [];
        let count = 0;
        const maxDist = 18;
        for (let i = 0; i < CONFIG.nodes && count < CONFIG.edges; i++) {
            for (let j = i + 1; j < CONFIG.nodes && count < CONFIG.edges; j++) {
                const dx = nodePositions[i * 3] - nodePositions[j * 3];
                const dy = nodePositions[i * 3 + 1] - nodePositions[j * 3 + 1];
                const dz = nodePositions[i * 3 + 2] - nodePositions[j * 3 + 2];
                const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
                if (dist < maxDist) {
                    edgeVerts.push(
                        nodePositions[i * 3], nodePositions[i * 3 + 1], nodePositions[i * 3 + 2],
                        nodePositions[j * 3], nodePositions[j * 3 + 1], nodePositions[j * 3 + 2]
                    );
                    count++;
                }
            }
        }
        return new Float32Array(edgeVerts);
    }

    const edgeGeo = new THREE.BufferGeometry();
    edgeGeo.setAttribute('position', new THREE.BufferAttribute(buildEdges(), 3));
    const edgeMat = new THREE.LineBasicMaterial({
        color: 0x6366f1, transparent: true, opacity: 0.08,
        blending: THREE.AdditiveBlending, depthWrite: false
    });
    const edgeLines = new THREE.LineSegments(edgeGeo, edgeMat);
    scene.add(edgeLines);

    // Ambient particles
    const pGeo = new THREE.BufferGeometry();
    const pPos = new Float32Array(CONFIG.particleCount * 3);
    for (let i = 0; i < CONFIG.particleCount; i++) {
        pPos[i * 3]     = (Math.random() - 0.5) * SPREAD * 3;
        pPos[i * 3 + 1] = (Math.random() - 0.5) * SPREAD * 2;
        pPos[i * 3 + 2] = (Math.random() - 0.5) * 40 - 20;
    }
    pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3));
    const pMat = new THREE.PointsMaterial({
        color: 0xd946ef, size: 0.4, transparent: true, opacity: 0.15,
        blending: THREE.AdditiveBlending, depthWrite: false
    });
    scene.add(new THREE.Points(pGeo, pMat));

    // Mouse parallax
    let mouseX = 0, mouseY = 0;
    document.addEventListener('mousemove', e => {
        mouseX = (e.clientX / window.innerWidth - 0.5) * 2;
        mouseY = (e.clientY / window.innerHeight - 0.5) * 2;
    });

    // Resize
    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });

    // Animation
    let lastTime = 0;
    const targetFPS = document.hidden ? 15 : 30;
    const frameInterval = 1000 / targetFPS;

    function animate(time) {
        requestAnimationFrame(animate);
        const delta = time - lastTime;
        if (delta < frameInterval) return;
        lastTime = time;

        // Move nodes
        for (let i = 0; i < CONFIG.nodes; i++) {
            const ix = i * 3, iy = i * 3 + 1, iz = i * 3 + 2;
            nodePositions[ix] += nodeVelocities[ix];
            nodePositions[iy] += nodeVelocities[iy];
            nodePositions[iz] += nodeVelocities[iz];

            if (Math.abs(nodePositions[ix]) > SPREAD) nodeVelocities[ix] *= -1;
            if (Math.abs(nodePositions[iy]) > SPREAD * 0.5) nodeVelocities[iy] *= -1;
            if (Math.abs(nodePositions[iz]) > 20) nodeVelocities[iz] *= -1;

            glowPositions[ix] = nodePositions[ix];
            glowPositions[iy] = nodePositions[iy];
            glowPositions[iz] = nodePositions[iz];
        }

        updateNodeInstances();
        glowGeo.attributes.position.needsUpdate = true;

        // Rebuild edges periodically (every ~120 frames)
        if (Math.floor(time / 4000) !== Math.floor((time - delta) / 4000)) {
            edgeGeo.setAttribute('position', new THREE.BufferAttribute(buildEdges(), 3));
        }

        // Camera parallax
        camera.position.x += (mouseX * 3 - camera.position.x) * 0.02;
        camera.position.y += (-mouseY * 2 - camera.position.y) * 0.02;
        camera.lookAt(0, 0, -10);

        // Subtle rotation
        scene.rotation.y = Math.sin(time * 0.0001) * 0.05;

        renderer.render(scene, camera);
    }

    // Throttle when tab hidden
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) renderer.setAnimationLoop(null);
    });

    requestAnimationFrame(animate);
})();
