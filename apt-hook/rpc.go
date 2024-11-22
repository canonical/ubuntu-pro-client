package main

import (
	"bufio"
	"encoding/json"
	"io"
	"net"
	"fmt"
	"os"
)

const (
	MethodHello      = "org.debian.apt.hooks.hello"
	MethodBye		 = "org.debian.apt.hooks.bye"
)

type Connection struct {
	conn net.Conn
	reader *bufio.Reader
}

// Close closes an existing connection.
func (c *Connection) Close() error {
	return c.conn.Close()
}

// ReadMessage reads a message from the connection.
func (c *Connection) ReadMessage() (*jsonRPC, error) {
	return readRPC(c.reader)
}

// WriteResponse writes a response to the connection.
func (c *Connection) WriteResponse(version string, id int) error {
	response := fmt.Sprintf(`{"jsonrpc": "2.0", "id": %d, "result": {"version": "%s"}}`, id, version)
	_, err := c.conn.Write([]byte(response + "\n\n"))
	return err
}

// Handshake performs the handshake with the connection by reading the hello message.
func (c *Connection) Handshake() error {
	msg, err := c.ReadMessage()
	if err != nil {
		return fmt.Errorf("reading handshake: %w", err)
	}

	if msg.Method != MethodHello {
		return fmt.Errorf("expected hello method, got: %v", msg.Method)
	}

	if err := c.WriteResponse("0.2", 0); err != nil {
		return fmt.Errorf("writing handshake response: %w", err)
	}

	return nil
}

// Bye sends a bye message to the connection by reading the bye message.
func (c *Connection) Bye() error {
	msg, err := c.ReadMessage()
	if err != nil {
		return fmt.Errorf("reading bye message: %w", err)
	}

	if msg.Method != MethodBye {
		return fmt.Errorf("expected bye method, got: %v", msg.Method)
	}

	return nil
}

// NewConnection creates a new connection to the specified socket.
func NewConnection(f *os.File) (*Connection, error) {
	conn, err := net.FileConn(f)
	if err != nil {
		return nil, err
	}
	return &Connection{
		conn: conn,
		reader: bufio.NewReader(conn),
	}, nil
}

func readRPC(r *bufio.Reader) (*jsonRPC, error) {
	line, err := r.ReadBytes('\n')
	if err != nil && err != io.EOF {
		return nil, err
	}

	var msg jsonRPC
	if err := json.Unmarshal(line, &msg); err != nil {
		return nil, fmt.Errorf("parsing json: %w", err)
	}

	emptyLine, _, err := r.ReadLine()

	if err != nil {
		return nil, fmt.Errorf("reading empty line: %w", err)
	}

	if string(emptyLine) != "" {
		return nil, fmt.Errorf("unexpected line: %q (empty)", emptyLine)
	}

	return &msg, nil
}
