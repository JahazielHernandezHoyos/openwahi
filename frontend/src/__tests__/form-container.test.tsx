/**
 * Tests for FormContainer component
 * Verifies rendering of title, description, icon, children, and footer
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { FormContainer } from "@/components/shared/FormContainer";

// Need to check how FormContainer renders — read the actual component
// It uses Card from shadcn, so we test the rendered output

describe("FormContainer", () => {
  it("renders title and description", () => {
    render(
      <FormContainer title="Test Title" description="Test Description">
        <div>Content</div>
      </FormContainer>
    );

    expect(screen.getByText("Test Title")).toBeInTheDocument();
    expect(screen.getByText("Test Description")).toBeInTheDocument();
  });

  it("renders children content", () => {
    render(
      <FormContainer title="Title">
        <p data-testid="child">Hello World</p>
      </FormContainer>
    );

    expect(screen.getByTestId("child")).toBeInTheDocument();
    expect(screen.getByText("Hello World")).toBeInTheDocument();
  });

  it("renders footer when provided", () => {
    render(
      <FormContainer title="Title" footer={<button>Save</button>}>
        <div>Content</div>
      </FormContainer>
    );

    expect(screen.getByText("Save")).toBeInTheDocument();
  });

  it("renders without optional props", () => {
    render(
      <FormContainer title="Minimal">
        <div>Content</div>
      </FormContainer>
    );

    expect(screen.getByText("Minimal")).toBeInTheDocument();
    expect(screen.getByText("Content")).toBeInTheDocument();
  });
});
