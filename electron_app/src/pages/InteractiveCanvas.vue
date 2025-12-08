<template>
    <div class="interactive-canvas-container">
        <!-- Top Toolbar for canvas controls -->
        <div class="canvas-toolbar">
            <!-- Mode Toggle Buttons -->
            <button @click="setMode('draw')" class="l_button button_small" :class="{ 'button_colored': current_mode === 'draw' }">Draw</button>
            <button @click="setMode('select')" class="l_button button_small" :class="{ 'button_colored': current_mode === 'select' }">Select</button>

            <span class="toolbar-divider"></span>

            <!-- Drawing Controls (Only visible in draw mode) -->
            <template v-if="current_mode === 'draw'">
                <label for="stroke-size">Stroke Size:</label>
                <input
                    id="stroke-size"
                    type="range"
                    min="1"
                    max="200"
                    v-model="stroke_size_no"
                >
            </template>

            <span class="toolbar-divider"></span>

            <button @click="clearCanvas" class="l_button button_medium">Clear</button>
            <span style="margin-left: auto;">Connection: <b :style="{ color: connection_status_color }">{{ connection_status }}</b></span>
        </div>

        <!-- Saved Commands Toolbar -->
        <div class="saved-commands-toolbar" v-if="saved_commands.length > 0">
            <span>Workflows:</span>
            <button
                v-for="(command, index) in saved_commands"
                :key="index"
                @click="executeCommand(command)"
                class="l_button button_small command-button"
            >
                {{ command.name }}
            </button>
        </div>

        <!-- The main drawing area -->
        <div class="canvas-area">
            <ImageCanvas
                ref="interactive_image_canvas"
                :stroke_size_no="stroke_size_no"
                :current_mode="current_mode"
                :image_source="blank_canvas_b64"
            ></ImageCanvas>
        </div>

        <!-- Bottom Command Bar -->
        <div class="command-bar">
            <input
                type="text"
                v-model="command_text"
                placeholder="Type command or prompt for selection..."
                @keyup.enter="handleCommandInput"
            >
            <button @click="handleCommandInput" class="l_button button_small" :disabled="is_generating">
                {{ button_text }}
            </button>
        </div>
    </div>
</template>

<script>
import ImageCanvas from '../components_bare/ImageCanvas.vue';
import { EventBus } from '../event_bus.js';
import { send_to_py } from "../py_vue_bridge.js";

function createBlankCanvas(width, height) {
    const c = document.createElement('canvas'); c.width=width; c.height=height;
    const ctx = c.getContext('2d'); ctx.fillStyle='white'; ctx.fillRect(0,0,width,height);
    return c.toDataURL();
}

const InteractiveCanvas = {
    name: 'InteractiveCanvas',
    props: { app: Object },
    components: { ImageCanvas },
    data() {
        return {
            current_mode: 'draw',
            selection_box: null, // Will store {x, y, width, height}
            is_generating: false,
            // --- other data properties ---
            stroke_size_no: "30",
            blank_canvas_b64: null,
            websocket: null,
            connection_status: "Connecting...",
            command_text: '',
            saved_commands: [],
        };
    },
    computed: {
        button_text() {
            if (this.is_generating) return "Generating...";
            if (this.selection_box) return "Generate for Selection";
            return "Save as Button";
        }
    },
    mounted() {
        this.blank_canvas_b64 = createBlankCanvas(1024, 768);
        this.loadCommandsFromLocalStorage();
        EventBus.$on('new-image-asset', this.handleNewImageAsset);
        EventBus.$on('selection-changed', (selection) => { this.selection_box = selection; });
        this.app.stable_diffusion.$watch('is_input_avail', (is_avail) => { this.is_generating = !is_avail; });
    },
    beforeDestroy() {
        EventBus.$off('new-image-asset', this.handleNewImageAsset);
        EventBus.$off('selection-changed');
    },
    methods: {
        setMode(mode) {
            this.current_mode = mode;
            if (this.$refs.interactive_image_canvas) {
                this.$refs.interactive_image_canvas.clearSelection();
            }
        },
        handleCommandInput() {
            if (this.selection_box && this.command_text.trim()) {
                this.executeInpaintingCommand();
            } else {
                this.saveCommand();
            }
        },
        executeInpaintingCommand() {
            if (!this.command_text.trim() || !this.selection_box || this.is_generating) return;

            const image_b64 = this.$refs.interactive_image_canvas.getStageAsBase64();
            const mask_b64 = this.$refs.interactive_image_canvas.getMaskFromSelection();
            if (!image_b64 || !mask_b64) return;

            const params = {
                "prompt": this.command_text,
                "is_inpaint": true,
                "input_image_b64": image_b64,
                "mask_image_b64": mask_b64,
                "selection_box": this.selection_box, // Pass selection box to backend
                "num_imgs": 1, "ddim_steps": 50, "guidance_scale": 7.5,
                "img_width": this.$refs.interactive_image_canvas.stage_config.width,
                "img_height": this.$refs.interactive_image_canvas.stage_config.height,
                "seed": Math.floor(Math.random() * 10000000),
            };

            this.is_generating = true;
            send_to_py("t2im " + JSON.stringify(params));
            this.command_text = '';
        },
        handleNewImageAsset(image_data) {
            if (this.$refs.interactive_image_canvas && image_data.generated_img_path) {
                const image_path = `file://${image_data.generated_img_path}?t=${new Date().getTime()}`;

                // --- THIS IS THE NEW LAYER LOGIC ---
                // We use the full generated image, but use Konva's clipping
                // function to only display the part within the selection box.
                this.$refs.interactive_image_canvas.addLayerFromImage(
                    image_path,
                    this.selection_box
                );

                // Reset selection and mode
                this.setMode('draw');
            }
        },
        clearCanvas() {
            this.blank_canvas_b64 = createBlankCanvas(1024, 768);
            if (this.$refs.interactive_image_canvas) {
                 this.$refs.interactive_image_canvas.clearAllLayers();
            }
        },
        // ... (other methods: saveCommand, executeCommand, etc.)
    },
};

// --- Full methods for context ---
InteractiveCanvas.methods.saveCommand = function() { /* ... as before ... */ };
InteractiveCanvas.methods.loadCommandsFromLocalStorage = function() { /* ... as before ... */ };
InteractiveCanvas.methods.executeCommand = function(command) { /* ... as before ... */ };


export default InteractiveCanvas;
// --- Export properties as before ---
</script>

<style scoped>
/* --- Styles as before --- */
</style>
