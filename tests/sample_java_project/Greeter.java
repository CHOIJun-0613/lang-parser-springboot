package com.example;

import java.io.PrintStream;

import com.test.Parent;

public class Greeter extends Parent{
    private String greeting = "Hello";
    public static final int MAX_VALUE = 100;
    private PrintStream printStream = System.out;

    public void sayHello() {
        printStream.println(greeting + ", World!");
        //System.out.println(greeting + ", World!");
    }
}
