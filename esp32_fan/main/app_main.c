#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "protocol_examples_common.h"
#include "driver/gpio.h"
#include "mqtt_client.h"
#include "esp_timer.h"

#define TAG "SMART_RELAY"
#define MOTION_GPIO 1
#define RELAY_GPIO 2
#define MOTION_TIMEOUT 300 // seconds

#define MQTT_STATE_TOPIC "foxyhamster/feeds/outlet-state"
#define MQTT_COMMAND_TOPIC "foxyhamster/feeds/outlet-set"

// --- State ---
static bool relay_state = false;
static int64_t last_motion_time = 0;
static esp_mqtt_client_handle_t mqtt_client = NULL;

// --- Set relay output and publish state ---
static void set_relay(bool state)
{
    relay_state = state;
    gpio_set_level(RELAY_GPIO, state ? 1 : 0);
    const char *payload = state ? "on" : "off";
    esp_mqtt_client_publish(mqtt_client, MQTT_STATE_TOPIC, payload, 0, 1, 0);
    ESP_LOGI(TAG, "Relay %s, published state", payload);
}

// --- MQTT event handler ---
static void mqtt_event_handler(void *handler_args, esp_event_base_t base, int32_t event_id, void *event_data)
{
    esp_mqtt_event_handle_t event = event_data;
    switch ((esp_mqtt_event_id_t)event_id)
    {
    case MQTT_EVENT_CONNECTED:
        ESP_LOGI(TAG, "MQTT Connected!");
        esp_mqtt_client_subscribe(event->client, MQTT_COMMAND_TOPIC, 1);
        set_relay(false); // Initialize relay to OFF
        break;
    case MQTT_EVENT_DATA:
        ESP_LOGI(TAG, "MQTT Data: TOPIC=%.*s DATA=%.*s",
                 event->topic_len, event->topic, event->data_len, event->data);
        if (strncmp(event->topic, MQTT_COMMAND_TOPIC, event->topic_len) == 0)
        {
            if (strncmp(event->data, "on", event->data_len) == 0)
            {
                set_relay(true);
            }
            else if (strncmp(event->data, "off", event->data_len) == 0)
            {
                set_relay(false);
            }
        }
        break;
    default:
        break;
    }
}

// --- Setup MQTT client ---
static void mqtt_app_start(void)
{
    esp_mqtt_client_config_t mqtt_cfg = {
        .broker.address.uri = "mqtt://io.adafruit.com",
        .credentials.username = "yourusername",              // <-- CHANGE TO YOUR ADAFRUIT IO USERNAME
        .credentials.authentication.password = "yourAIOkey", // <-- CHANGE TO YOUR ADAFRUIT IO KEY
    };

    mqtt_client = esp_mqtt_client_init(&mqtt_cfg);
    esp_mqtt_client_register_event(mqtt_client, ESP_EVENT_ANY_ID, mqtt_event_handler, NULL);
    esp_mqtt_client_start(mqtt_client);
}

// --- Main motion/relay logic loop ---
static void motion_task(void *pvParameters)
{
    gpio_set_direction(MOTION_GPIO, GPIO_MODE_INPUT);
    gpio_set_direction(RELAY_GPIO, GPIO_MODE_OUTPUT);
    set_relay(false);

    while (1)
    {
        int motion = gpio_get_level(MOTION_GPIO);

        if (motion)
        {
            last_motion_time = esp_timer_get_time() / 1000000; // seconds
            if (!relay_state)
                set_relay(true);
        }

        int64_t now = esp_timer_get_time() / 1000000; // seconds

        if (relay_state && (now - last_motion_time) >= MOTION_TIMEOUT)
        {
            set_relay(false);
        }

        vTaskDelay(pdMS_TO_TICKS(100)); // poll every 100 ms
    }
}

void app_main(void)
{
    ESP_LOGI(TAG, "[APP] Startup..");
    ESP_ERROR_CHECK(nvs_flash_init());
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    ESP_ERROR_CHECK(example_connect()); // connect Wi-Fi

    mqtt_app_start(); // start MQTT

    // Small delay to allow MQTT to connect before starting motion loop
    vTaskDelay(pdMS_TO_TICKS(3000));

    xTaskCreate(motion_task, "motion_task", 4096, NULL, 5, NULL);
}
