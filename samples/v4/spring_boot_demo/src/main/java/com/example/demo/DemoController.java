package com.example.demo;

import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/demo")
public class DemoController {
    @GetMapping("/hello")
    public String hello() {
        return "hello";
    }

    @PostMapping("/submit")
    public String submit(@RequestBody String payload) {
        return payload;
    }
}