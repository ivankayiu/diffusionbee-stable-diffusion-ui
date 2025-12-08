<template>
    <div ref="container" class="konva-container">
        <v-stage :config="stage_config" ref="stage" @mousedown="handleMouseDown" @mousemove="handleMouseMove" @mouseup="handleMouseUp" @click="handleClick">
            <v-layer ref="imageLayer"></v-layer>
            <v-layer ref="generatedLayer"></v-layer>
            <v-layer ref="selectionLayer">
                <!-- Transformer is added programmatically -->
            </v-layer>
        </v-stage>
    </div>
</template>

<script>
import Konva from 'konva';
import { EventBus } from '../event_bus.js';

export default {
    name: 'ImageCanvas',
    props: {
        image_source: String,
        current_mode: String,
        stroke_size_no: String,
    },
    data() {
        return {
            stage_config: { width: 512, height: 512 },
            is_drawing: false,
            last_line: null,
            selection_rect: null,
            transformer: null,
        };
    },
    mounted() {
        this.fitStageIntoParent();
        window.addEventListener('resize', this.fitStageIntoParent);
        if (this.image_source) this.loadImage(this.image_source);

        // Initialize Transformer
        const transformer = new Konva.Transformer({ nodes: [] });
        this.$refs.selectionLayer.getNode().add(transformer);
        this.transformer = transformer;
    },
    beforeDestroy() { window.removeEventListener('resize', this.fitStageIntoParent); },
    methods: {
        fitStageIntoParent() { /* ... */ },
        loadImage(src) { /* ... */ },

        handleMouseDown(e) {
            if (e.target.getParent() instanceof Konva.Transformer) return; // Ignore clicks on transformer handles
            if (this.current_mode === 'select' || e.target.hasName('generated_image')) {
                // If in select mode, or clicking a generated image, deselect everything first
                this.transformer.nodes([]);
            }
            // --- Rest of mousedown logic for drawing or starting a new selection ---
            const pos = this.$refs.stage.getNode().getPointerPosition();
            if (this.current_mode === 'draw' && !e.target.hasName('generated_image')) {
                this.is_drawing = true;
                this.last_line = new Konva.Line({ /* ... line properties ... */ });
                this.$refs.imageLayer.getNode().add(this.last_line);
            } else if (this.current_mode === 'select') {
                this.is_drawing = true;
                this.selection_rect = new Konva.Rect({ x: pos.x, y: pos.y, /* ... rect properties ... */ });
                this.$refs.selectionLayer.getNode().add(this.selection_rect);
            }
        },

        handleMouseMove(e) { /* ... as before ... */ },
        handleMouseUp() {
            this.is_drawing = false;
            if (this.current_mode === 'select' && this.selection_rect) {
                const box = this.selection_rect.getAttrs();
                EventBus.$emit('selection-changed', box.width > 0 ? box : null);
            }
        },

        handleClick(e) {
            // This logic handles selecting a generated image to transform it.
            if (this.current_mode !== 'select' && e.target.hasName('generated_image')) {
                this.transformer.nodes([e.target]);
            } else {
                this.transformer.nodes([]);
            }
        },

        addLayerFromImage(image_path, box) {
            const generatedLayer = this.$refs.generatedLayer.getNode();
            Konva.Image.fromURL(image_path, (konvaImage) => {
                konvaImage.setAttrs({
                    x: box.x,
                    y: box.y,
                    width: box.width,
                    height: box.height,
                    draggable: true,
                    name: 'generated_image', // Name for easy selection
                });
                generatedLayer.add(konvaImage);
                this.transformer.nodes([konvaImage]); // Auto-select the new layer
            });
        },

        clearAllLayers() { /* ... */ },
        clearSelection() { /* ... */ },
        getStageAsBase64() { /* ... */ },
        getMaskFromSelection() { /* ... */ },
    },
    // --- watch, etc. ---
};

// --- Full methods for context ---
Object.assign(InteractiveCanvas.methods, {
    fitStageIntoParent() {
        const container = this.$refs.container;
        if (!container) return;
        this.stage_config.width = container.offsetWidth;
        this.stage_config.height = container.offsetHeight;
    },
    loadImage(src) {
        const imageLayer = this.$refs.imageLayer.getNode();
        const image = new window.Image();
        image.src = src;
        image.onload = () => {
            const img = new Konva.Image({ image: image, width: this.stage_config.width, height: this.stage_config.height });
            imageLayer.add(img);
            img.moveToBottom();
        };
    },
    handleMouseMove(e) {
        if (!this.is_drawing) return;
        const pos = this.$refs.stage.getNode().getPointerPosition();
        if (this.current_mode === 'draw' && this.last_line) {
            this.last_line.points(this.last_line.points().concat([pos.x, pos.y]));
        } else if (this.current_mode === 'select' && this.selection_rect) {
            const x1 = this.selection_rect.x();
            const y1 = this.selection_rect.y();
            this.selection_rect.width(pos.x - x1);
            this.selection_rect.height(pos.y - y1);
        }
    },
    clear_inpaint() {
        const imageLayer = this.$refs.imageLayer.getNode();
        imageLayer.find('Line').forEach(l => l.destroy());
    },
    clearAllLayers() {
        this.clear_inpaint();
        const generatedLayer = this.$refs.generatedLayer.getNode();
        generatedLayer.destroyChildren();
        this.transformer.nodes([]);
    },
    clearSelection() {
        if (this.selection_rect) {
            this.selection_rect.destroy();
            this.selection_rect = null;
        }
        EventBus.$emit('selection-changed', null);
    },
    getStageAsBase64() {
        // Temporarily hide transformer before exporting
        this.transformer.hide();
        const dataURL = this.$refs.stage.getNode().toDataURL();
        this.transformer.show();
        return dataURL;
    },
    getMaskFromSelection() {
        if (!this.selection_rect) return null;
        const tempLayer = new Konva.Layer();
        tempLayer.add(new Konva.Rect({ x:0, y:0, width: this.stage_config.width, height: this.stage_config.height, fill: 'black' }));
        tempLayer.add(new Konva.Rect({ ...this.selection_rect.getAttrs(), fill: 'white' }));
        return tempLayer.toDataURL();
    }
});

export default InteractiveCanvas;
</script>
