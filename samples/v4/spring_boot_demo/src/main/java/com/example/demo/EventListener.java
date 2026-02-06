package com.example.demo;

import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Component
public class EventListener {
    @KafkaListener(topics = "demo-topic")
    public void handle(String message) {
        // handle event
    }
}