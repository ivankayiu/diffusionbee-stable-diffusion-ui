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
        // eslint-disable-next-line no-unused-vars
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

        // eslint-disable-next-line no-unused-vars
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
</script>
